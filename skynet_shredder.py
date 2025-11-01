#!/usr/bin/env python3
# Skynet Shredder v1.1 (English)
# PyQt5 GUI for secure file & directory deletion (HDD/SSD aware)
#
# NOTES ON SECURITY:
# - On HDDs, multiple overwrites via `shred` are effective.
# - On SSDs, due to wear-leveling, per-file overwrites are not guaranteed.
#   This tool deletes files and proactively issues TRIM (fstrim) for the mount.
#   For whole-disk secure erase on SSDs, use manufacturer tools or `blkdiscard`
#   / `nvme format` at your own risk (NOT exposed by default in this GUI).
#
# Dependencies: python3, PyQt5, coreutils (shred), util-linux (fstrim, findmnt)

import os
import sys
import subprocess
import shutil
import pathlib
from dataclasses import dataclass
from typing import List, Tuple, Optional

from PyQt5 import QtWidgets, QtGui, QtCore

APP_NAME = "Skynet Shredder"
VERSION = "1.1"

RED = "#ff2b2b"
DARK = "#0b0b0b"
ACCENT = "#e60000"

def which(prog: str) -> Optional[str]:
    return shutil.which(prog)

def run(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate()
        return proc.returncode, out, err
    except Exception as e:
        return 1, "", str(e)

def get_mountpoint(path: str) -> Optional[str]:
    rc, out, err = run(["findmnt", "-T", path, "-no", "TARGET"])
    if rc == 0:
        return out.strip()
    p = pathlib.Path(path).resolve()
    while p != p.parent:
        if os.path.ismount(str(p)):
            return str(p)
        p = p.parent
    return None

def get_block_device_for_path(path: str) -> Optional[str]:
    rc, out, err = run(["findmnt", "-T", path, "-no", "SOURCE"])
    if rc != 0:
        return None
    return out.strip() or None

def is_rotational_device(dev: str) -> Optional[bool]:
    try:
        if dev.startswith("/dev/mapper/"):
            rc, out, err = run(["lsblk", "-no", "PKNAME", dev])
            if rc == 0 and out.strip():
                base = out.strip()
            else:
                rc, out, err = run(["lsblk", "-no", "NAME", dev])
                if rc == 0 and out.strip():
                    base = out.strip().splitlines()[-1]
                else:
                    base = None
        else:
            name = os.path.basename(dev)
            if name.startswith("nvme"):
                base = "".join(name.split("p")[:1])
                rc, out, err = run(["lsblk", "-no", "PKNAME", dev])
                if rc == 0 and out.strip():
                    base = out.strip()
            else:
                base = ''.join([c for c in name if not c.isdigit()])
                rc, out, err = run(["lsblk", "-no", "PKNAME", dev])
                if rc == 0 and out.strip():
                    base = out.strip()
        if not base:
            return None
        path = f"/sys/block/{base}/queue/rotational"
        if os.path.exists(path):
            with open(path) as f:
                val = f.read().strip()
                return val == "1"
        return None
    except Exception:
        return None

@dataclass
class TargetItem:
    path: str

class DropList(QtWidgets.QListWidget):
    files_dropped = QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(self.ExtendedSelection)
        self.setStyleSheet("QListWidget { background: #111; color: #eee; border: 1px solid #333; }")

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        e.acceptProposedAction()

    def dropEvent(self, e: QtGui.QDropEvent):
        paths = []
        for url in e.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(local)
        if paths:
            self.files_dropped.emit(paths)

class LogView(QtWidgets.QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)
        self.setStyleSheet("QPlainTextEdit { background: #0a0a0a; color: #e6e6e6; border: 1px solid #300; }")

    def log(self, text: str):
        self.appendPlainText(text)

class ShredWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(int)
    status = QtCore.pyqtSignal(str)
    finished_ok = QtCore.pyqtSignal()
    finished_err = QtCore.pyqtSignal(str)

    def __init__(self, paths: List[str], passes: int, gutmann: bool, ssd_mode: bool, trim_after: bool):
        super().__init__()
        self.paths = paths
        self.passes = passes
        self.gutmann = gutmann
        self.ssd_mode = ssd_mode
        self.trim_after = trim_after
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        total = len(self.paths)
        done = 0
        mountpoints_to_trim = set()

        shred_prog = which("shred")
        srm_prog = which("srm")
        fstrim_prog = which("fstrim")

        for p in self.paths:
            if self._stop:
                break
            try:
                if not os.path.exists(p):
                    self.status.emit(f"[!] Not found: {p}")
                    done += 1
                    self.progress.emit(int(done * 100 / total))
                    continue

                mp = get_mountpoint(p) or "/"
                dev = get_block_device_for_path(p) or ""
                rotational = is_rotational_device(dev)
                rotational_str = {True: "HDD", False: "SSD", None: "Unknown"}.get(rotational, "Unknown")
                self.status.emit(f"[i] Target: {p}  (Mount: {mp}, Device: {dev}, Type: {rotational_str})")

                if os.path.isdir(p):
                    all_files = []
                    for root, dirs, files in os.walk(p, topdown=False):
                        for name in files:
                            all_files.append(os.path.join(root, name))
                    for f in all_files:
                        self._wipe_file(f, shred_prog, srm_prog, rotational, mp)
                    for root, dirs, files in os.walk(p, topdown=False):
                        for d in dirs:
                            dpath = os.path.join(root, d)
                            try:
                                os.rmdir(dpath)
                            except Exception:
                                pass
                    try:
                        os.rmdir(p)
                    except Exception:
                        pass
                else:
                    self._wipe_file(p, shred_prog, srm_prog, rotational, mp)

                mountpoints_to_trim.add(mp)
                done += 1
                self.progress.emit(int(done * 100 / total))
            except Exception as e:
                self.status.emit(f"[ERR] {p}: {e}")

        if self.trim_after and fstrim_prog and mountpoints_to_trim:
            for mp in mountpoints_to_trim:
                self.status.emit(f"[TRIM] fstrim {mp} ...")
                rc, out, err = run([fstrim_prog, "-v", mp])
                if rc == 0:
                    self.status.emit(out.strip())
                else:
                    self.status.emit(f"[WARN] fstrim failed on {mp}: {err.strip()}")

        if done == total:
            self.finished_ok.emit()
        else:
            self.finished_err.emit("Interrupted")

    def _wipe_file(self, f: str, shred_prog: Optional[str], srm_prog: Optional[str], rotational: Optional[bool], mountpoint: str):
        try:
            if rotational is True:
                if shred_prog:
                    cmd = [shred_prog, "-v"]
                    if self.gutmann:
                        cmd += ["-n", "35"]
                    else:
                        cmd += ["-n", str(max(1, self.passes))]
                    cmd += ["-z", "-u", f]
                    self.status.emit(f"[HDD] shred: {' '.join(cmd)}")
                    rc, out, err = run(cmd)
                    self.status.emit(out.strip())
                    if rc != 0 and err.strip():
                        self.status.emit(f"[WARN] shred error: {err.strip()}")
                else:
                    if srm_prog:
                        cmd = [srm_prog, "-vz"]
                        if self.gutmann:
                            cmd += ["-s"]
                        cmd += [f]
                        self.status.emit(f"[HDD] srm: {' '.join(cmd)}")
                        rc, out, err = run(cmd)
                        self.status.emit(out.strip() or err.strip())
                    else:
                        try:
                            size = os.path.getsize(f)
                            with open(f, "wb") as fh:
                                fh.write(os.urandom(min(size, 1024*1024)))
                            os.remove(f)
                            self.status.emit(f"[HDD] Fallback: 1x overwritten and removed: {f}")
                        except Exception as e:
                            self.status.emit(f"[ERR] {f}: {e}")

            elif rotational is False:
                try:
                    if os.path.isfile(f):
                        try:
                            size = os.path.getsize(f)
                            with open(f, "r+b") as fh:
                                block = os.urandom(1024*1024)
                                fh.seek(0)
                                fh.write(block)
                                if size > 2*1024*1024:
                                    fh.seek(size - 1024*1024)
                                    fh.write(block)
                                fh.flush()
                                os.fsync(fh.fileno())
                        except Exception:
                            pass
                    os.remove(f)
                    self.status.emit(f"[SSD] File removed (TRIM will run after completion): {f}")
                except Exception as e:
                    self.status.emit(f"[ERR] {f}: {e}")
            else:
                if shred_prog:
                    cmd = [shred_prog, "-v", "-n", str(max(1, self.passes)), "-z", "-u", f]
                    if self.gutmann:
                        cmd = [shred_prog, "-v", "-n", "35", "-z", "-u", f]
                    self.status.emit(f"[?] shred: {' '.join(cmd)}")
                    rc, out, err = run(cmd)
                    self.status.emit(out.strip())
                    if rc != 0 and err.strip():
                        self.status.emit(f"[WARN] shred error: {err.strip()}")
                else:
                    os.remove(f)
                    self.status.emit(f"[?] Fallback: removed: {f}")

        except Exception as e:
            self.status.emit(f"[ERR] {f}: {e}")

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setMinimumSize(920, 640)
        self.setWindowIcon(QtGui.QIcon(self._icon_path()))
        self._build_ui()
        self.worker: Optional[ShredWorker] = None

    def _icon_path(self):
        cand = [
            os.path.join(os.path.dirname(__file__), "assets", "icon.png"),
            "icon.png"
        ]
        for c in cand:
            if os.path.exists(c):
                return c
        return ""

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        title = QtWidgets.QLabel(f"<h1 style='color:{RED};'>SKYNET SHREDDER</h1>")
        subtitle = QtWidgets.QLabel("<span style='color:#aaa;'>Secure Delete • HDD/SSD aware • Recursive</span>")

        self.list = DropList()
        self.list.files_dropped.connect(self.add_paths)

        add_btn = QtWidgets.QPushButton("Add files/folders")
        add_btn.clicked.connect(self.add_dialog)

        rem_btn = QtWidgets.QPushButton("Remove selected")
        rem_btn.clicked.connect(self.remove_selected)

        clear_btn = QtWidgets.QPushButton("Clear list")
        clear_btn.clicked.connect(self.list.clear)

        passes_label = QtWidgets.QLabel("Passes:")
        self.passes_spin = QtWidgets.QSpinBox()
        self.passes_spin.setRange(1, 35)
        self.passes_spin.setValue(3)

        self.gutmann_chk = QtWidgets.QCheckBox("Gutmann (35x)")
        self.gutmann_chk.stateChanged.connect(self._gutmann_toggle)

        self.ssd_chk = QtWidgets.QCheckBox("Force SSD optimization (TRIM after delete)")
        self.ssd_chk.setChecked(True)

        self.trim_chk = QtWidgets.QCheckBox("Run fstrim on affected mountpoints after completion")
        self.trim_chk.setChecked(True)

        warn = QtWidgets.QLabel(f"<span style='color:{ACCENT};'>Warning: This action is irreversible.</span>")

        self.log = LogView()

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)

        shred_btn = QtWidgets.QPushButton("⚠️ Secure Delete")
        shred_btn.clicked.connect(self.start_shred)

        layout = QtWidgets.QGridLayout(central)
        layout.addWidget(title, 0, 0, 1, 3)
        layout.addWidget(subtitle, 1, 0, 1, 3)
        layout.addWidget(self.list, 2, 0, 1, 3)
        layout.addWidget(add_btn, 3, 0)
        layout.addWidget(rem_btn, 3, 1)
        layout.addWidget(clear_btn, 3, 2)
        layout.addWidget(passes_label, 4, 0)
        layout.addWidget(self.passes_spin, 4, 1)
        layout.addWidget(self.gutmann_chk, 4, 2)
        layout.addWidget(self.ssd_chk, 5, 0, 1, 3)
        layout.addWidget(self.trim_chk, 6, 0, 1, 3)
        layout.addWidget(warn, 7, 0, 1, 3)
        layout.addWidget(self.progress, 8, 0, 1, 3)
        layout.addWidget(shred_btn, 9, 0, 1, 3)
        layout.addWidget(self.log, 10, 0, 1, 3)

        self.setStyleSheet(f"""
            QWidget {{ background: {DARK}; color: #ddd; font-family: 'JetBrainsMono Nerd Font', monospace; }}
            QPushButton {{ background: #1b1b1b; border: 1px solid #333; padding: 8px; border-radius: 8px; }}
            QPushButton:hover {{ border: 1px solid {RED}; }}
            QProgressBar {{ background: #111; border: 1px solid #333; border-radius: 6px; text-align: center; }}
            QProgressBar::chunk {{ background: {RED}; }}
            QCheckBox, QLabel {{ color: #ccc; }}
        """)

        self.setAcceptDrops(True)

    def _gutmann_toggle(self):
        if self.gutmann_chk.isChecked():
            self.passes_spin.setEnabled(False)
        else:
            self.passes_spin.setEnabled(True)

    def add_paths(self, paths: List[str]):
        for p in paths:
            p = os.path.abspath(p)
            if not os.path.exists(p):
                continue
            item = QtWidgets.QListWidgetItem(p)
            self.list.addItem(item)

    def add_dialog(self):
        dlg = QtWidgets.QFileDialog(self, "Select files/folders")
        dlg.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        if dlg.exec_():
            sel = dlg.selectedFiles()
            self.add_paths(sel)
        dirp = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder")
        if dirp:
            self.add_paths([dirp])

    def remove_selected(self):
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))

    def start_shred(self):
        paths = [self.list.item(i).text() for i in range(self.list.count())]
        if not paths:
            QtWidgets.QMessageBox.warning(self, APP_NAME, "Please select at least one file or folder.")
            return

        reply = QtWidgets.QMessageBox.warning(
            self, "Confirmation",
            "This will PERMANENTLY delete the selected files/folders.\nContinue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        passes = self.passes_spin.value()
        gutmann = self.gutmann_chk.isChecked()
        ssd_mode = self.ssd_chk.isChecked()
        trim_after = self.trim_chk.isChecked()

        self.progress.setValue(0)
        self.log.log(f"==> Start: {len(paths)} target(s), passes={passes if not gutmann else 35}, SSD-optimization={'on' if ssd_mode else 'off'}, TRIM={'on' if trim_after else 'off'}")
        self.worker = ShredWorker(paths, passes, gutmann, ssd_mode, trim_after)
        self.worker.status.connect(self.log.log)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished_ok.connect(lambda: self.log.log("==> Finished."))
        self.worker.finished_err.connect(lambda msg: self.log.log(f"==> Completed with error: {msg}"))
        self.worker.start()

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QtGui.QDropEvent):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.add_paths(paths)

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = Main()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
