from pathlib import Path
import shutil
import program_files.globals as global_variables
from program_files.logger import logger
import os

project_dir = Path(global_variables.project_dir).resolve()
if not getattr(global_variables, "project_dir", None):
    raise RuntimeError("Project directory not set in global_variables.project_dir")

def _check_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(project_dir):
        logger.error(f"Access denied: {path} is outside project directory.")
        raise PermissionError(f"Access denied: {path} is outside project directory.")
    return path

def _check_path_exception(path):
    user_home = Path.home()
    path = Path(path).resolve()

    is_in_home = user_home in path.parents
    if not is_in_home:
        logger.error(f"Access denied: {path} is outside of user folder.")
        raise PermissionError(f"Access denied: {path} is outside of user folder.")
    return path

def copytree(src, dst, *args, **kwargs):
    _check_path(src)
    _check_path(dst)
    logger.info(f"Copy folder {src} to {dst}")
    return shutil.copytree(src, dst, *args, **kwargs)

def move(src, dst, exception=False, *args, **kwargs):
    if exception:
        _check_path_exception(src)
        _check_path_exception(dst)
        logger.info(f"Move folder {src} to {dst}")
    else:
        _check_path(src)
        _check_path(dst)
        logger.info(f"Move folder {src} to {dst}")
    return shutil.move(src, dst, *args, **kwargs)

def rmtree(path, *args, **kwargs):
    _check_path(path)
    logger.info(f"Remove folder {path}")
    return shutil.rmtree(path, *args, **kwargs)

def copy(src, dst, *args, **kwargs):
    _check_path(src)
    _check_path(dst)
    logger.info(f"Copy file {src} to {dst}")
    return shutil.copy(src, dst, *args, **kwargs)

def copy2(src, dst, *args, **kwargs):
    _check_path(src)
    _check_path(dst)
    return shutil.copy2(src, dst, *args, **kwargs)

def remove(path):
    _check_path(path)
    logger.info(f"Remove file {path}")
    os.remove(path)

def rename(src, dst):
    _check_path(src)
    _check_path(dst)
    logger.info(f"Rename file from {src} to {dst}")
    os.rename(src, dst)

for name in dir(shutil):
    if not globals().get(name):  # Nur übernehmen, wenn noch nicht selbst definiert
        globals()[name] = getattr(shutil, name)