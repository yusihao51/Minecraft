# Imports, sorted alphabetically.

# Python packages
# Nothing for now...

# Third-party packages
# Nothing for now...

# Modules from this project
# Nothing for now...
from timer import Timer

__all__ = (
    'PhysicsTask', 'PhysicsManager', 'physics_manager',
)

PHYSICS_TIMER_INTERVAL = PHYSICS_TICK = 0.1

class PhysicsTask(object):
	def __init__(self, position, accel, obj):
		self.accel = accel
		self.velocity = [0, 0, 0]
		self.falling_time = 0
		self.falling_height = 0
		self.obj = obj
		self.position = list(position)

class PhysicsManager(object):
	def __init__(self):
		self.timer = Timer(PHYSICS_TIMER_INTERVAL, "physics_timer")
		self.started = False
		self.tasks = []

	def __del__(self):
		self.timer.stop()

	def update(self):
		if len(self.tasks) == 0:
			self.started = False
			self.timer.stop()
			return

		for task in self.tasks:
			vy = task.velocity[1]
			for i in [0, 1, -1]:
				v0 = task.velocity[i]
				task.velocity[i] += task.accel[i] * PHYSICS_TIMER_INTERVAL
				task.position[i] += (v0 + task.velocity[i]) / 2.0 * PHYSICS_TIMER_INTERVAL
			task.falling_time += PHYSICS_TIMER_INTERVAL
			task.falling_height += abs(task.velocity[1] + vy) / 2.0 * PHYSICS_TIMER_INTERVAL
			task.obj.update_position(task.position)

		self.timer.add_task(PHYSICS_TICK, self.update)

	# do physics to an object which has:
	#   * method update_position(position) to update its position
	def do_physics(self, position, accel, obj):
		self.tasks.append(PhysicsTask(position, accel, obj))
		if not self.started:
			self.started = True
			self.timer.add_task(PHYSICS_TICK, self.update)
			self.timer.start()

physics_manager = PhysicsManager()
