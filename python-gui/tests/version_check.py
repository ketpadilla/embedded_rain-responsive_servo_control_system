# AI-Generated
import serial
import tkinter

try:
    print("pyserial version:", serial.__version__)
except AttributeError:
    print("pyserial version could not be determined.")

try:
    # TkVersion is a float representing the Tcl/Tk version
    print("Tkinter version (TkVersion):", tkinter.TkVersion) 
    root = tkinter.Tk()
    root.title("Test Version Check")
    # Tcl/Tk patchlevel can provide more detailed version info
    print("Tkinter patchlevel:", root.tk.call('info', 'patchlevel')) 
    root.destroy()
except Exception as e:
    print(f"Tkinter version could not be determined or an error occurred: {e}")