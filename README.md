# Skynet Shredder

Secure GUI file/dir deletion for Linux (HDD/SSD-aware). PyQt5.

## Features
- Drag & Drop files/folders
- Recursive delete for directories
- HDD: multi-pass overwrite via `shred` (1–35 passes / Gutmann)
- SSD: delete + `fstrim` on mountpoints (TRIM) for best-effort secure wipe
- Live log & progress bar
- Dark Skynet theme; custom icon

## Install (Debian 13)
```bash
sudo apt update
sudo apt install -y python3 python3-pyqt5 coreutils util-linux findmnt
# Run locally
python3 skynet_shredder.py
```

## Optional tools
- `srm` (secure-delete package) as fallback
```bash
sudo apt install secure-delete
```

## Notes
- On SSDs, true per-file secure overwrite is not guaranteed due to wear-leveling.
  This app deletes files and triggers TRIM (`fstrim`) on the corresponding mountpoints.
- For whole-disk secure-erase: use manufacturer utilities, `blkdiscard`, or `nvme format`
  (dangerous; not exposed by default).
