import tkinter as tk
from PIL import Image, ImageTk

from gui import PipelineGUI


def main():
    root = tk.Tk()

    try:
        image = Image.open('C:/Users/agers/D/RGU/srt/icon.png')
        photo = ImageTk.PhotoImage(image)
        root.iconphoto(False, photo)
    except Exception:
        pass

    PipelineGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
