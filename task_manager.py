import os
import json
import config_manager

def get_tasks_file():
    return config_manager.get_tasks_file()

def load_tasks():
    tasks_path = get_tasks_file()
    if not os.path.exists(tasks_path):
        return []
    try:
        with open(tasks_path, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_tasks(tasks):
    tasks_path = get_tasks_file()
    os.makedirs(os.path.dirname(tasks_path), exist_ok=True)
    with open(tasks_path, "w") as f:
        json.dump(tasks, f, indent=4)

def add_task(title, priority="Normal"):
    tasks = load_tasks()
    new_task = {
        "id": max([t.get("id", 0) for t in tasks], default=0) + 1,
        "title": title,
        "status": "Pending",
        "priority": priority
    }
    tasks.append(new_task)
    save_tasks(tasks)
    return new_task

def complete_task(task_id=None, title=None):
    tasks = load_tasks()
    found = False
    for task in tasks:
        if task_id and task.get("id") == task_id:
            task["status"] = "Completed"
            found = True
        elif title and title.lower() in task.get("title", "").lower():
            task["status"] = "Completed"
            found = True
    
    if found:
        save_tasks(tasks)
    return found

def get_pending_tasks():
    tasks = load_tasks()
    return [t for t in tasks if t.get("status") == "Pending"]

def remove_task(task_id=None, title=None):
    tasks = load_tasks()
    initial_count = len(tasks)
    
    if task_id:
        tasks = [t for t in tasks if t.get("id") != task_id]
    elif title:
        tasks = [t for t in tasks if title.lower() not in t.get("title", "").lower()]
        
    if len(tasks) < initial_count:
        save_tasks(tasks)
        return True
    return False
