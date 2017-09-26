############
# Standard #
############
import time
import logging
###############
# Third Party #
###############


##########
# Module #
##########
from roadrunner import BlockWatch

logging.basicConfig(level='INFO')

#Configuration
##############
notepad_prefix   = "MFX:RR"
ai_prefix        = "MFX:USR:ai1:0"
filter_prefix    = "MFX:ATT:10"
sequencer_prefix = "ECS:SYS0:7"
min_threshold    = 1.0

def main():
    #Instantiate blocker
    try:
        print("Loading Watcher ...")
        wb = BlockWatch(notepad_prefix,
                        ai_prefix,
                        filter_prefix,
                        sequencer_prefix,
                        threshold=min_threshold)

    except Exception as exc:
        print(exc)
    #Wait for signals
    print("Waiting for signals ...")
    wb.run()

if __name__ == "__main__":
    main()
