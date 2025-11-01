# 🔥 Skynet Shredder v1.0

> **“There is no fate but what we make… and what we shred.”**  
A futuristic, GUI-based file and folder shredder for Linux — *HDD & SSD aware, recursive, TRIM-enabled*, and themed after a certain self-aware machine network.  
Secure delete has never looked this cool.

---

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](#)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-ready-lightgreen.svg)](#)

---

## 🚀 Features

- **Drag & Drop** files and folders into the GUI  
- **Recursive deletion** of entire directories  
- **HDD Mode**: Secure multi-pass overwrite via `shred` (1–35 passes or Gutmann)  
- **SSD Mode**: Smart delete with post-wipe TRIM (`fstrim`)  
- **Live console log** + progress bar in a dark Skynet-inspired UI  
- Supports *Linux-based systems*, especially **Debian 13** and Ubuntu  
- No cloud, no tracking, no mercy.  

---

## 🧠 How it works

| Drive Type | Method Used                                      |
|------------|--------------------------------------------------|
| **HDD**    | `shred -n X -z -u` (multi-pass overwrite + delete) |
| **SSD**    | File delete + secure TRIM via `fstrim -v <mount>` |
| **Unknown**| Uses user-selected mode (shred or TRIM)          |

> ⚠️ On SSDs, due to wear-leveling, secure overwriting of *individual files* is not guaranteed.  
> That’s why Skynet Shredder uses TRIM to unmap deleted blocks. Want 100% wipe? Use full-disk secure erase.

---

## 📦 Installation
🖥️ Run locally (no install)

python3 skynet_shredder.py

## ⚙️ Install system-wide (adds application shortcut)

./install.sh

## 🤖 For Contributors

Got ideas? Want to add your own “Judgment Day Mode” with secure full-drive wipe?
Feel free to open an issue or submit a PR. Just don't anger the machines.

## 🛡️ License

This project is licensed under the MIT License.
Feel free to fork, improve, and create your own self-aware systems — responsibly, of course.

### 🔧 Requirements (Debian 13 / Ubuntu 22+)

```bash
sudo apt update
sudo apt install -y python3 python3-pyqt5 coreutils util-linux

