import sys
import os
import time

import zenframe.application

BIND_TOKEN = None
EXECPATH = sys.argv[0]





def smooth_stop_world():
	trace("common_unbouded_proc::smooth_stop_world")
	
	if ANIMATE_THREAD:
		ANIMATE_THREAD.finish()

	if close_handle:
		close_handle()
	
	class final_waiter_thr(QThread):
		def run(self):
			procs = psutil.Process().children()
			trace(procs)
			psutil.wait_procs(procs, callback=on_terminate)
			app.quit()

	#nonlocal THREAD_FINALIZER
	#THREAD_FINALIZER = final_waiter_thr()
	#THREAD_FINALIZER.start()

def stop_world():
	trace("common_unbouded_proc::stop_world")
	if IS_STARTER:
		return smooth_stop_world()

	MAIN_COMMUNICATOR.stop_listen()
	if ANIMATE_THREAD:
		ANIMATE_THREAD.finish()

	if CONSOLE_RETRANS_THREAD:
		CONSOLE_RETRANS_THREAD.finish()			

	if close_handle:
		close_handle()

	trace("FINISH UNBOUNDED QTAPP : app quit on receive")
	app.quit()
	trace("app quit on receive... after")

def receiver(data):
	trace("common_unbouded_proc::receiver")
	try:
		data = pickle.loads(data)
		trace(data)
		if data["cmd"] == "stopworld": 
			stop_world()
		elif data["cmd"] == "smooth_stopworld": 
			smooth_stop_world()
		elif data["cmd"] == "stop_activity":
			stop_activity()
		elif data["cmd"] == "console":
			sys.stdout.write(data["data"])
		else:
			widget.external_communication_command(data)
	except Exception as ex:
		print_to_stderr("common_unbouded_proc::receiver", ex)




def bind(winid, debug=False, debugcomm=False):
	if BIND_TOKEN is None:
		# Запуск из консоли. Нужно создать процесс и прибиндиться к нему.

		session_id = 0

		communicator = zenframe.application.start_unbound_zenframe(tgtpath=EXECPATH)
		#time.sleep(2)
		communicator.send({
			"cmd":"bindwin", 
			"id":int(winid), 
			"pid":os.getpid(), 
			"session_id":session_id
		})

		communicator.newdata.connect(receiver)
		communicator.oposite_clossed.connect(stop_world)
		communicator.smooth_stop.connect(smooth_stop_world)

	else:
		# Запуск из фрейма песочницы. Нужно должить туда о готовности.
		pass

