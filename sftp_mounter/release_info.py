def print_release_steps():
    steps = """
============================================================
           SFTP MOUNTER - RELEASE CHECKLIST
============================================================

1. Check for updates of external dependencies:
   - Check the latest Rclone version at: https://github.com/rclone/rclone/releases
   - Check the latest WinFsp version at: https://github.com/winfsp/winfsp/releases
   - If updates are available, update the download links in:
     sftp_mounter/package.py

2. Increment project version number in the following locations:
   - pyproject.toml -> [tool.poetry] version = "X.Y.Z"
   - sftp_mounter/main.py -> app.setApplicationVersion("X.Y.Z")
   - sftp_mounter/package.py -> VERSION = "X.Y.Z"

3. Verify translations & English defaults:
   - Ensure all new strings are translated in sftp_mounter/i18n.py
   - Ensure English is set as the default/fallback language.

4. Run syntax verification checks:
   - poetry run python -m py_compile sftp_mounter/*.py

5. Test the application locally:
   - poetry run sftp-mounter

6. Build the standalone Windows executable:
   - poetry run python sftp_mounter/package.py
     (Creates the redistributable dist/SFTPMounter-vX.Y.Z.exe)

7. Commit changes & create a Git release tag:
   - git add .
   - git commit -m "Release version X.Y.Z"
   - git tag -a vX.Y.Z -m "Version X.Y.Z"
   - git push origin main --tags

============================================================
"""
    print(steps)
