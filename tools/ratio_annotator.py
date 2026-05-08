import argparse
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog

import cv2
import numpy as np


class RatioAnnotator:
    def __init__(self, img, output_path="annotations.json"):
        self.img = img
        self.h, self.w = img.shape[:2]
        self.output_path = output_path

        self.start = None
        self.end = None
        self.drawing = False
        self.boxes = []
        self.box_ids = []

        self.root = None
        self.canvas = None
        self.current_rect_id = None
        self.status_label = None
        self.tk_image = None

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.start = (x, y)
            self.drawing = True
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            self.end = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.end = (x, y)
            self.drawing = False
            self._add_box_from_points(self.start, self.end)

    def _add_box_from_points(self, start, end):
        if not start or not end:
            return None

        x1, y1 = start
        x2, y2 = end
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)
        width = right - left
        height = bottom - top

        if width < 5 or height < 5:
            return None

        ratio = {
            "top": round(top / self.h, 6),
            "left": round(left / self.w, 6),
            "width": round(width / self.w, 6),
            "height": round(height / self.h, 6),
        }
        box_data = {
            "pixels": {"top": top, "left": left, "width": width, "height": height},
            "ratios": ratio,
        }
        self.boxes.append(box_data)
        self._print_box(box_data)
        return box_data

    def _print_box(self, box_data):
        pixels = box_data["pixels"]
        ratios = box_data["ratios"]
        print("\n====== New annotation ======")
        print(
            "Pixels: "
            f"top={pixels['top']}, left={pixels['left']}, "
            f"w={pixels['width']}, h={pixels['height']}"
        )
        print(
            "Ratios: "
            f"top={ratios['top']:.4f}, left={ratios['left']:.4f}, "
            f"width={ratios['width']:.4f}, height={ratios['height']:.4f}"
        )

    def _make_tk_image(self):
        rgb = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
        ppm = b"P6 %d %d 255\n" % (self.w, self.h) + rgb.tobytes()
        return tk.PhotoImage(data=ppm)

    def _update_status_label(self):
        if self.status_label:
            self.status_label.config(text=f"Resolution: {self.w}x{self.h} | Boxes: {len(self.boxes)}")

    def _save_boxes(self):
        if not self.boxes:
            print("\n[No annotations to save]")
            return

        save_path = self._select_save_path()
        if not save_path:
            print("\n[Save canceled]")
            return

        with open(save_path, "w", encoding="utf-8") as handle:
            json.dump(self.boxes, handle, indent=4)
        print(f"\n[Saved {len(self.boxes)} annotations to {save_path}]")

    def _select_save_path(self):
        root = tk.Tk()
        root.attributes("-topmost", True)
        root.withdraw()
        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=self.output_path,
            title="Save annotations",
        )
        root.update()
        root.destroy()
        return save_path

    def _canvas_coords(self, event):
        return int(self.canvas.canvasx(event.x)), int(self.canvas.canvasy(event.y))

    def _start_draw(self, event):
        self.start = self._canvas_coords(event)
        self.drawing = True
        if self.current_rect_id:
            self.canvas.delete(self.current_rect_id)
            self.current_rect_id = None

    def _update_draw(self, event):
        if not self.drawing:
            return
        self.end = self._canvas_coords(event)
        if self.current_rect_id:
            self.canvas.delete(self.current_rect_id)
        self.current_rect_id = self.canvas.create_rectangle(
            *self.start,
            *self.end,
            outline="red",
            width=2,
        )

    def _finish_draw(self, event):
        if not self.drawing:
            return
        self.end = self._canvas_coords(event)
        self.drawing = False
        if self.current_rect_id:
            self.canvas.delete(self.current_rect_id)
            self.current_rect_id = None

        box_data = self._add_box_from_points(self.start, self.end)
        if not box_data:
            return

        pixels = box_data["pixels"]
        rect_id = self.canvas.create_rectangle(
            pixels["left"],
            pixels["top"],
            pixels["left"] + pixels["width"],
            pixels["top"] + pixels["height"],
            outline="green",
            width=2,
        )
        self.box_ids.append(rect_id)
        self._update_status_label()

    def _undo(self):
        if not self.boxes:
            return
        self.boxes.pop()
        if self.box_ids:
            self.canvas.delete(self.box_ids.pop())
        print("\n[Undid last annotation]")
        self._update_status_label()

    def _clear(self):
        for rect_id in self.box_ids:
            self.canvas.delete(rect_id)
        self.box_ids = []
        self.boxes = []
        print("\n[Cleared all annotations]")
        self._update_status_label()

    def _on_key(self, event):
        key = event.keysym.lower()
        if key in ("q", "escape"):
            self.root.quit()
        elif key == "c":
            self._clear()
        elif key == "z":
            self._undo()
        elif key == "s":
            self._save_boxes()

    def _run_tkinter(self):
        self.root = tk.Tk()
        self.root.title("Ratio Annotator")

        self.tk_image = self._make_tk_image()
        self.canvas = tk.Canvas(
            self.root,
            width=min(self.w, 1280),
            height=min(self.h, 720),
            scrollregion=(0, 0, self.w, self.h),
        )
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        hbar = tk.Scrollbar(self.root, orient="horizontal", command=self.canvas.xview)
        vbar = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<ButtonPress-1>", self._start_draw)
        self.canvas.bind("<B1-Motion>", self._update_draw)
        self.canvas.bind("<ButtonRelease-1>", self._finish_draw)
        self.root.bind("<Key>", self._on_key)
        self.root.focus_set()

        self.status_label = tk.Label(
            self.root,
            text=f"Resolution: {self.w}x{self.h} | Boxes: {len(self.boxes)}",
            anchor="w",
        )
        self.status_label.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        help_label = tk.Label(
            self.root,
            text="Drag: annotate   z: undo   c: clear   s: save   q/ESC: quit",
            anchor="w",
        )
        help_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))

        _print_help()
        self.root.mainloop()

    def run(self):
        window_name = "Ratio Annotator"
        try:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, min(self.w, 1280), min(self.h, 720))
            cv2.setMouseCallback(window_name, self.mouse_callback)
        except cv2.error:
            self._run_tkinter()
            return

        _print_help()
        while True:
            display = self.img.copy()
            for box in self.boxes:
                pixels = box["pixels"]
                cv2.rectangle(
                    display,
                    (pixels["left"], pixels["top"]),
                    (
                        pixels["left"] + pixels["width"],
                        pixels["top"] + pixels["height"],
                    ),
                    (0, 255, 0),
                    2,
                )

            if self.drawing and self.start and self.end:
                cv2.rectangle(display, self.start, self.end, (0, 0, 255), 2)

            info_text = f"Resolution: {self.w}x{self.h} | Boxes: {len(self.boxes)}"
            cv2.rectangle(display, (5, 5), (390, 35), (0, 0, 0), -1)
            cv2.putText(
                display,
                info_text,
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            cv2.imshow(window_name, display)
            key = cv2.waitKey(20) & 0xFF

            if key in (27, ord("q")):
                break
            if key == ord("c"):
                self.boxes.clear()
                print("\n[Cleared all annotations]")
            elif key == ord("z"):
                if self.boxes:
                    self.boxes.pop()
                    print("\n[Undid last annotation]")
            elif key == ord("s"):
                self._save_boxes()

        cv2.destroyAllWindows()


def _print_help():
    print("\n--- Controls ---")
    print("Left mouse drag: draw a box")
    print("z: undo last box")
    print("c: clear all boxes")
    print("s: save annotations to JSON")
    print("q or ESC: quit\n")


def _choose_image():
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    selected_file = filedialog.askopenfilename(
        title="Choose an image to annotate",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All files", "*.*")],
    )
    root.update()
    root.destroy()
    return selected_file


def _load_image(path: str):
    try:
        img_array = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception as exc:
        print(f"Failed to read image: {exc}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image ratio bounding box annotator")
    parser.add_argument("-i", "--image", type=str, default="screenshot.png", help="Input image path")
    parser.add_argument("-o", "--output", type=str, default="annotations.json", help="Output JSON path")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print("Default image was not found. Choose an image in the file dialog.")
        selected = _choose_image()
        if not selected:
            print("No image selected. Exiting.")
            sys.exit(0)
        args.image = selected

    img = _load_image(args.image)
    if img is None:
        print(f"Could not decode image file: {args.image}")
        sys.exit(1)

    RatioAnnotator(img, output_path=args.output).run()
