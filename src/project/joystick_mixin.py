import pygame

from project.config import (
    movement_sensitivity, num_axes, LATCHED
)

# Handles joystick interaction & function
# Note: Currently only handles at most one joystick
class JoystickMixin():
    def __init__(self) -> None:
        # TODO: add item for latch
        self.joystick = None
        self.js_prev_pos = [0] * num_axes
        self.js_enabled = False

    def initialize_joystick(self):
        '''Find and initialize joystick, if one is connected'''
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            print("No joystick detected.")
        try:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Connected to: {self.joystick.get_name()}")
        except Exception as e:
            self.joystick = None
            print(f"Joystick Connection Error: {e}")

    def get_pos(self, axis: int) -> float:
        '''Get current position of the given joystick axis; updates
        self.js_prev_pos; returns 0xffffffff if no joystick is connected'''
        if (self.joystick is not None):
            pygame.event.pump()
            self.js_prev_pos[axis] = round(self.joystick.get_axis(axis), movement_sensitivity)
            return self.js_prev_pos[axis]
        return 0xffffffff

    def joystick_moved(self, axis: int, latch_axis) -> tuple[bool, float]:
        '''Returns True and joystick's current position if joystick is connected AND is in a different position from
        when this function was last called, else returns False and 0; updates self.js_prev_pos'''
        if self.joystick is not None and not self.is_latched(latch_axis):
            pygame.event.pump()
            pos = round(self.joystick.get_axis(axis), movement_sensitivity)
            if (pos != self.js_prev_pos[axis]):
                self.js_prev_pos[axis] = pos
                return [True, pos]
            else:
                self.js_prev_pos[axis] = pos
        return [False, 0]
    
    def is_latched(self, axis) -> bool:
        if self.joystick is not None:
            pygame.event.pump() # update position
            return round(self.joystick.get_axis(axis)) == LATCHED
        else:
            return True # default state is latched (locked)

    def set_joystick_enabled(self, state: bool) -> None:
        '''Set enabled to state'''
        self.js_enabled = state

    def get_joystick_enabled(self) -> bool:
        '''Returns True if joystick is connected and enabled, False otherwise'''
        return self.js_enabled and (self.joystick is not None)

    