############
# Standard #
############
import time
import logging
import multiprocessing

############
# External #
############
import zmq

##########
# Module #
##########
from roadrunner     import ChipProgrammer
from roadrunner.zmq import Request, Response

logger = logging.getLogger()

def test_zmq():
    #Create our programmer in a background thread
    def start_programmer(port):
        serv = ChipProgrammer("*:%s" % port)
        serv.start()
    #Create server process and start
    logger.debug("Starting server process ...")
    programmer_proc = multiprocessing.Process(target=start_programmer,
                                              args=("5556",), daemon=True)
    programmer_proc.start()
    time.sleep(5) #Ensure the background process has begun
    #Create client socket
    logger.debug("Creating client socket ...")
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5556")
    logger.debug("Testing protocols ...")
    #GET
    socket.send_json(Request("GET", "keys"))
    assert 'address' in socket.recv_json()[1]
    #POST
    socket.send_json(Request("POST", {"value" : 0}))
    resp = socket.recv_json()
    assert resp[0] == 1
    socket.send_json(("GET", "value"))
    assert socket.recv_json()[1] == 0
    socket.send_json(("GET", "keys"))
    assert 'value' in socket.recv_json()[1]
    #failed request on duplication
    socket.send_json(Request("POST", {"value" : 0}))
    resp = socket.recv_json()
    assert resp[0] == 0
    #PUT
    socket.send_json(Request("PUT", {"value" : 2}))
    resp = socket.recv_json()
    assert resp[0] == 1
    socket.send_json(("GET", "value"))
    assert socket.recv_json()[1] == 2
    #put new value
    socket.send_json(Request("PUT", {"param" : 2}))
    resp = socket.recv_json()
    assert resp[0] == 0
    #DELETE
    socket.send_json(Request("DELETE", "value"))
    resp = socket.recv_json()
    assert resp[0] == 1
    socket.send_json(("GET", "value")) == 0
    assert socket.recv_json()[0] == 0
    socket.send_json(("GET", "keys"))
    assert 'value' not in socket.recv_json()[1]
    #Invalid command
    socket.send_json(Request("COMMAND", "value"))
    resp = socket.recv_json()
    assert resp[0] == 0
    #Cleanup after tests
    programmer_proc.terminate()
    programmer_proc.join()
