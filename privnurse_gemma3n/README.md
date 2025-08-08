# 🏥 PrivNurse Environment Setup and Installation Guide

| ![Discharge Note Summarization](..\assets\Discharge_Note_Summarization.png) | ![Consulation Nursing Note_Summarization](..\assets\Consulation_Nursing_Note_Summarization.png)|
|---|---|

## 📋 System Architecture Overview

PrivNurse is a complete healthcare system that includes the following four main components:

* **Frontend**: Next.js web application
* **Backend**: Python Flask/FastAPI server
* **Database**: MySQL database
* **AI Model**: Ollama local large language model

---

## 🖥️ Using Tmux to Manage Services

### Tmux Split-Screen Configuration

After completing the installation of all components, use tmux to manage frontend and backend services simultaneously:

#### 1. Create and Configure a Tmux Session

```bash
# Create a new tmux session (if not already created)
tmux new-session -d -s privnurse

# Enter the tmux session
tmux attach-session -t privnurse

# Rename the current window
tmux rename-window 'PrivNurse'
```

#### 2. Split the Screen

```bash
# Vertically split the screen (left/right)
# Inside tmux, press Ctrl+B then %
# Or run the following command
tmux split-window -h

# Horizontally split the right panel (top/bottom)
# First move to the right panel: Ctrl+B then press →
# Then press Ctrl+B then "
tmux split-window -v
```

#### 3. Panel Configuration and Service Startup

After configuration, there will be three panels:

* **Left panel**: Database management and monitoring
* **Top right panel**: Backend service
* **Bottom right panel**: Frontend service

```bash
# Panel 1 (left) - Database monitoring
# Move to left panel: Ctrl+B then press ←
docker ps | grep mysql
docker logs -f privnurse_mysql

# Panel 2 (top right) - Backend service
# Move to top right panel: Ctrl+B then press ↑
cd /path/to/privnurse
source venv/bin/activate
python3 local_server.py

# Panel 3 (bottom right) - Frontend service
# Move to bottom right panel: Ctrl+B then press ↓
cd /path/to/privnurse
npm run start
```

#### 4. Common Tmux Shortcuts

| Shortcut             | Function                                    |
| -------------------- | ------------------------------------------- |
| `Ctrl+B` → `%`       | Vertical split                              |
| `Ctrl+B` → `"`       | Horizontal split                            |
| `Ctrl+B` → `←/→/↑/↓` | Move between panels                         |
| `Ctrl+B` → `x`       | Close current panel                         |
| `Ctrl+B` → `d`       | Detach from session (services keep running) |
| `Ctrl+B` → `c`       | Create a new window                         |
| `Ctrl+B` → `,`       | Rename window                               |

#### 5. Service Management Commands

```bash
# View all tmux sessions
tmux list-sessions

# Attach to an existing session
tmux attach-session -t privnurse

# Detach from a session (services keep running)
# Inside tmux: press Ctrl+B then d

# Completely terminate a session
tmux kill-session -t privnurse

# View windows in a session
tmux list-windows -t privnurse

# View panes in a specific window
tmux list-panes -t privnurse:0
```

---

## 🚀 Initial Setup

### 1. File Preparation

```bash
# Clone Repository
git https://github.com/weilin1205/PrivNurseAI.git

cd PrivNurseAI/privnurse_gemma3n
```

### 2. Tmux Work Environment Setup

```bash
# Create a new tmux session
tmux new-session -d -s privnurse

# Enter the tmux session
tmux attach-session -t privnurse
```

---

## 💻 Frontend Setup (Next.js)

### Environment Configuration

1. **Copy environment configuration file**

   ```bash
   cp .env.local.example .env.local
   ```

2. **Edit environment variables**

   ```bash
   nano .env.local
   ```

   Set the content:

   ```
   NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP:8000
   ```

   > 💡 Replace `YOUR_SERVER_IP` with the actual server IP address, do not add a slash after the URL
   > 💡 The downloaded file has port 8080 by default, remember to change it

3. **Firewall Configuration**

   ```bash
   # Ensure the firewall allows access to relevant ports
   sudo ufw allow 8087  # Frontend port (can be adjusted in package.json)
   sudo ufw allow 8000  # Backend port (can be changed in local_server.py line 34)
   ```

### Installation and Startup

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Start the frontend service
npm run start
```

---

## 🐍 Backend Setup (Python)

### Environment Configuration

1. **Copy environment configuration file**

   ```bash
   cp .env.example .env
   ```

2. **Edit database configuration**

   ```bash
   nano .env
   ```

   Set the content:

   ```
   MYSQL_USER=
   MYSQL_PASSWORD=
   MYSQL_HOST=localhost
   MYSQL_PORT=3307
   MYSQL_DB=inference_db
   ```

### Python Environment Setup

#### Method 1: Use existing venv

The downloaded files already include a venv

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac

# Start backend server
python3 local_server.py
```

#### Method 2: Create a new venv (if Method 1 fails)

```bash
# Remove old virtual environment
rm -rf venv

# Create a new virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start backend server
python3 local_server.py
```

---

## 🗄️ Database Setup (MySQL)

### Prerequisites

Ensure Docker is installed:

* [Docker Installation Guide](https://weilin1205.github.io/posts/docker/)

### Installation and Startup

```bash
# Start MySQL container
docker run -d \
  --name privnurse_mysql \
  -e MYSQL_ROOT_PASSWORD=my-secret-pw \
  -e MYSQL_DATABASE=inference_db \
  -p 3307:3306 \
  --restart unless-stopped \
  mysql:latest
```

> ⚠️ **Important**: Replace `my-secret-pw` with a secure password and fill it in the `.env` file

---

## 🤖 AI Model Setup (Ollama)

### Install Ollama

```bash
# Run automatic installation script
curl -fsSL https://ollama.com/install.sh | sh
```

### Model Download and Configuration (Example)

```bash
# Download summary model (name contains "summary")
ollama pull llama2-summary

# Download validation model (name contains "validation")
ollama pull llama2-validation
```

---

## 🎯 System Usage Instructions

### Model Selection Rules

After installation, the system's model page will display two selection areas:

1. **Summary model field**

   * Displays Ollama models with names containing `summary`
   * Used for document summarization

2. **Highlight model field**

   * Displays Ollama models with names containing `validation`
   * Used for content validation and annotation

### Startup Order

It is recommended to use tmux to manage the service startup order:

1. **Start database service** (left panel)

   ```bash
   docker start privnurse_mysql
   ```

2. **Start backend service** (top right panel)

   ```bash
   source venv/bin/activate
   python3 local_server.py
   ```

3. **Start frontend service** (bottom right panel)

   ```bash
   npm run start
   ```

4. **Check Ollama service**

   ```bash
   ollama serve  # If not already running
   ```

### Access the System

* Frontend page: `http://localhost:8087`
* Backend API: `http://localhost:8000`
* Database: `localhost:3307`

### Port Configuration

* **Frontend port 8087**: adjustable in `package.json` scripts
* **Backend port 8000**: changeable in `local_server.py` line 34
* **Database port 3307**: avoids conflict with default MySQL port

---

## 🔧 Common Troubleshooting

### Port Conflicts

```bash
# Check port usage
sudo netstat -tlnp | grep :8087
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :3307

# To modify port settings:
# Frontend: edit start script in package.json
# Backend: edit line 34 in local_server.py
```

### Service Status Check

```bash
# Check Docker container status
docker ps

# Check Ollama service
ollama list

# Check Python processes
ps aux | grep python

# Check all panel statuses in tmux
tmux list-panes -t privnurse -F "#{pane_index}: #{pane_current_command}"
```

### Log Viewing

```bash
# View Docker container logs
docker logs privnurse_mysql

# View Next.js logs
npm run start --verbose

# In tmux, view service logs in real-time
# Left panel: docker logs -f privnurse_mysql
# Top right panel: backend service console output
# Bottom right panel: frontend service console output
```

### Tmux Troubleshooting

```bash
# If tmux session is unresponsive
tmux kill-session -t privnurse
./start_privnurse.sh

# Reload tmux configuration
tmux source-file ~/.tmux.conf

# Check tmux version
tmux -V
```

---

## 📚 Related Resources

* [Next.js Documentation](https://nextjs.org/docs)
* [Docker Installation Guide](https://weilin1205.github.io/posts/docker/)
* [Ollama Official Website](https://ollama.com/)
* [MySQL Documentation](https://dev.mysql.com/doc/)
