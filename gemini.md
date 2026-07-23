# Developer Guide & Project Architecture

This document outlines the current architecture, development workflow, and technical details of the **SFTP Mounter** project. It is intended for developers and AI assistants working on this codebase.

---

## 🖥️ System & Platform Constraints

*   **Windows-Only:** The application is designed exclusively for Windows (10/11) because it relies on the WinFsp driver and Windows-native drive letter mapping (`net use`).
*   **Linux/macOS Development (via Wine):** Since the tool runs only on Windows, Linux developers can run and package the application using Wine (see [Development Tasks](#development-tasks)).

---

## ⚙️ Core Architecture & Components

### 1. WinFsp Driver Detection
To avoid issues with non-standard setups, the driver detection in [mounter.py](file:///home/worky/Proyectos/sftp_mounter/sftp_mounter/mounter.py) runs 6 fallback strategies:
*   Windows Registry scan (checking Uninstall GUID keys).
*   Kernel service lookup.
*   System directories check.
*   Environment `PATH` search for `launcherd.exe`.
*   *Failsafe:* The **Connect & Mount** button remains enabled even if detection fails, allowing users to attempt connection at their own risk (with a warning panel).

### 2. SSH Host Key Validation (`known_hosts`)
*   Validates host keys against the system default `~/.ssh/known_hosts` file.
*   If a host key is missing, it prompts the user to add it, calling `ssh-keyscan` under the hood.
*   *Failsafe:* If writing to `known_hosts` is blocked (e.g., due to permissions), the application falls back to connecting without verification (bypassing host-key check) for that session to prevent blocking the mount.

### 3. Log Cleanup & Single-Instance Prevention
*   **Startup Log Purge:** Before logging initialization in [main.py](file:///home/worky/Proyectos/sftp_mounter/sftp_mounter/main.py), it purges any existing `app.log` files. If a file is locked, the exception is caught silently and written to `stderr`.
*   **Instance Lock:** Uses `QLockFile` to restrict execution to a single instance. If another instance is running, it prompts the user and terminates cleanly (`sys.exit(0)`).

### 4. UI Layout & Settings
*   **Window Metrics:** The main GUI window is configured with a minimum size of `560 x 780` px to support high-DPI displays without text clipping.
*   **Layout Structure:** The connection form fields utilize a structured column grid to maintain responsiveness when SSH private key option inputs are toggled.
*   **Settings Dialog:** Located in [gui.py](file:///home/worky/Proyectos/sftp_mounter/sftp_mounter/gui.py), it allows users to manage application language (defaulting to English with dynamic Spanish fallbacks), startup behavior, tray minimization, and volume format.
*   **Volume Name Format (`conn_in_volname`):** A config parameter. When set to `False` (default), the drive volume name matches the profile name. When `True`, it includes the connection details (`user@host!port`).

---

## 🛠️ Development Tasks

### Local Windows Development
If running on a native Windows machine:
1.  **Install dependencies:**
    ```bash
    poetry install
    ```
2.  **Run the application:**
    ```bash
    poetry run sftp-mounter
    ```
3.  **Compile standalone executable:**
    ```bash
    poetry run python sftp_mounter/package.py
    ```
    *Generates a single, versioned `.exe` with embedded binaries inside `dist/`.*

### Linux Wine Development
If developing on Linux/macOS:
1.  **Configure Windows Python inside Wine:**
    ```bash
    poetry run poe setup-wine-python
    ```
2.  **Run code in Wine:**
    ```bash
    poetry run poe run-wine
    ```
3.  **Build Windows executable via Wine:**
    ```bash
    poetry run poe build-windows-wine
    ```

---

## 📂 Key Path References

During execution, the application reads/writes to these paths on the user's system:
*   **Logs:** `%APPDATA%\SFTPMounter\app.log`
*   **Configuration & Profiles:** `%APPDATA%\SFTPMounter\config.json`
*   **Embedded Binaries:** `%APPDATA%\SFTPMounter\bin\` (stores the extracted `rclone.exe`)
