import customtkinter as ctk
from gui.app import DrowsinessApp

if __name__ == "__main__":
    # Ensure High DPI awareness on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
        
    root = ctk.CTk()
    app = DrowsinessApp(root)
    
    # Handle clean exit
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()
