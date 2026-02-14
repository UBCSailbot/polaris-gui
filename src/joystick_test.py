import pygame
import time

pygame.init()
pygame.joystick.init()

# Check for connected joysticks
if pygame.joystick.get_count() == 0:
    print("No joystick detected.")
    exit()

js = pygame.joystick.Joystick(0)
js.init()

print(f"Connected to: {js.get_name()}")
try:
    # Get joystick data
    while True:
        pygame.event.pump() # Update joystick state

        # Read axis data
        x = js.get_axis(0) # right joystick left/right !!! the one I want
        y = js.get_axis(1) # right joystick up/down
        z = js.get_axis(2) # left joystick up/down
        a = js.get_axis(3) # left joystick left/right  !!! the one I want


        print(f"A = {a:.2f}")
        # print(f"X = {x:.2f}, Y = {y:.2f}, Z = {z:.2f}")

        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nExiting...")
    pygame.quit()