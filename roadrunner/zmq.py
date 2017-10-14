"""
ZMQ Interface for roadrunner
"""
############
# Standard #
############
import logging
import multiprocessing
from collections import namedtuple

############
# External #
############
import zmq

##########
# Module #
##########

logger = logging.getLogger()

#Request and response forms
Request   = namedtuple('Request',  ('req_code', 'info'))
Response  = namedtuple('Response', ('ret_code', 'info', 'msg'))

class ChipProgrammer:
    """
    Class to absorb chip parameters from a remote client

    In order to provide a system agnostic method for a remote user to control
    the chip parameters, ChipProgrammer holds user supplied chip information
    sent by 0MQ. Clients can either :meth:`.get`, :meth:`.put`, :meth:`.post`
    or :meth:`.delete` metadata about the chip and it will be stored internally
    for access later.

    Parameters
    ----------
    address : str or tuple
        Address of a 0MQ proxy, either in the form ``'127.0.1.1:3485'`` or
        ``('127.0.1.1','3485')``

    hostname : str, optional
        Only process responses from this host

    Attributes
    ----------
    methods : tuple
        Available commands

    chip : dict
        Storage for chip parameters. Also contains the `address` of the clients
        as well as all current information stored underneath `keys`
    """
    methods = ('GET', 'PUT', 'POST', 'DELETE')

    def __init__(self, address):
        #Split address if given as a string
        if isinstance(address, str):
            address = address.split(':', maxsplit=1)
        #Store address and hostname
        self.address = (address[0], int(address[1]))
        #Create context and socket
        logger.info("Creating server ...")
        #Storage from chip information
        self.chip  = {'address' : self.address,
                      'keys'    : list()}
        self.chip['keys'] = list(self.chip.keys())
        self._thread = None

    def _poll(self):
        self._context = zmq.Context()
        self._socket  = self._context.socket(zmq.REP)
        url = "tcp://%s:%d" % self.address
        self._socket.bind(url)
        while True:
            #Wait to receive request from socket
            request = self._socket.recv_json()
            logger.debug("Received request %r", request)
            #Make a default response
            try:
                request = Request(*request)
                #Handle unknown request types
                if request.req_code not in self.methods:
                    raise ValueError("Unknown request type : %s",
                                     request.req_code)
                #Perform request
                func = getattr(self, request.req_code.lower())
                resp = Response(1,
                                func(request.info),
                                'Succesfully executed : {}'
                                ''.format(request.req_code))
            #Handle exceptions
            except Exception as exc:
                logger.error("Request %s failed : %r",
                             request.req_code, exc)
                resp = Response(0, dict(), repr(exc))
            #Reply to client
            finally:
                logger.debug("Sending response %r", resp)
                self._socket.send_json(resp)

    def get(self, value):
        """
        Get a previously stored piece of information to the store
        """
        logger.info("Retreiving %s from parameter storage ...",
                    value)
        return self.chip[value]

    def put(self, info):
        """
        Assign new values to previously loaded value

        Parameters
        ----------
        info : dict
            Values to be updated. Keys need to already exist in the store
        """
        logger.info("Updating stored values for %s ...",
                    ", ".join(info.keys()))
        #See if we raise a KeyError, otherwise update
        for k,v in info.items():
            if k not in self.chip:
                raise KeyError("Key %s not found. Use POST", k)
        #Update storage
        self.chip.update(info)

    def post(self, info):
        """
        Create new entries in the chip parameter store

        Parameters
        ----------
        info : dict
            Values to be added to the dictionary. Can not overwite existing
            keys
        """
        logger.info("Adding keys %s to stored parameter list ...",
                    ', '.join(info.keys()))
        for k,v in info.items():
            if k in self.chip:
                raise ValueError("Duplicate key %s. Use PUT", k)
        #Update storage
        self.chip.update(info)
        self.chip['keys'].extend(list(info.keys()))

    def delete(self, value):
        """
        Delete a piece of information from the parameter store
        """
        logger.info("Destroying stored parameter %s ...", value)
        self.chip.pop(value)
        self.chip['keys'].remove(value)

    def start(self):
        """
        Start the server
        """
        try:
            self._thread = multiprocessing.Process(target=self._poll)
            self._thread.start()
            self._thread.join()
        #Catch any exception
        except:
            #Cleanup
            self.stop()
            #Reraise
            raise

    def stop(self):
        """
        Stop the server and cleanup
        """
        #Stop the thread if it is running
        if self._thread is not None:
            self._thread.terminate()
            self._thread.join()
        #Cleanup the prior thread
        self._context = None
        self._socket  = None
        self._thread  = None
