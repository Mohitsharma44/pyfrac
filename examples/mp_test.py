import multiprocessing as mp
import time

def worker():
    while True:
        try:
            print("Every second, Ill print this")
            time.sleep(1)
        except KeyboardInterrupt as ki:
            print("[MP]: KI!")
            cleanup()
            break
        except Exception as ex:
            print("[MP]: EX!" + str(ex))
            cleanup()
            break

def cleanup():
    print("running some cleanup ... ")
            
def kill_child(*processes):
    for proc in processes:
        proc.terminate()
            
if __name__ == "__main__":
    manager = mp.Manager()
    event = manager.Event()
    process = mp.Process(target=worker)
    try:
        process.start()
        process.join()
    except KeyboardInterrupt as ki:
        print("[Main]: KI!")
    except Exception as ex:
        print("[Main]: EX!" + str(ex))
