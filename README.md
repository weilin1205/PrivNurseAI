# PrivNurse AI: Revolutionizing Clinical Documentation with On-Device Intelligence
> Empowering Healthcare Professionals with Secure, Offline-Ready AI that Transforms Medical Documentation While Keeping Patient Data Protected

**Authors: Wei-Lin Wen, Yu-Yao Tsai**

1. **Project Demo Video**: [Youtube Demo Link](https://youtu.be/gfFrrqFYB-s?si=UwFKngUBT0wq_RlK)
2. **Full Technical Report:** [Technical Report Link](https://github.com/weilin1205/PrivNurseAI/blob/main/PrivNurseAI_Technical_Report.pdf)
3. **Code Repository:** [github.com/weilin1205/PrivNurseAI](https://github.com/weilin1205/PrivNurseAI/tree/main)
4. **Key Components:** [Speech-to-Text Server](https://github.com/weilin1205/PrivNurseAI/tree/main/ExpertAgentC_LLMServer_Nursing_Note_STT) | [Data Preprocessing](https://github.com/weilin1205/PrivNurseAI/tree/main/Data_Preprocessing) | [Model Fine-tuning](https://github.com/weilin1205/PrivNurseAI/tree/main/FineTuning_Training) | [Teacher-Student Distillation](https://github.com/weilin1205/PrivNurseAI/tree/main/Training_Data_Distillation) | [Implementation](https://github.com/weilin1205/PrivNurseAI/tree/main/privnurse_gemma3n)

## **🚀 Executive Summary**

<img src="/assets/PrivNurseAI_architecture_0802.png" alt="Architecture" style="zoom:85%;" />

PrivNurse AI is an end-to-end, on-premises artificial intelligence system designed to combat one of the most pressing issues in modern healthcare: clinician burnout driven by administrative overload. By harnessing the unparalleled on-device efficiency and multimodal capabilities of Google's Gemma 3n, PrivNurse AI empowers nurses and physicians by automating and accelerating the creation of complex clinical documentation. The system features three core modules: an intelligent **Consultation Note Summarizer** that uses Chain-of-Thought reasoning to discern clinical priorities, a structured **Discharge Note Summarizer**, and a hands-free **Speech-to-Text Nursing Note Transcriber**. Deployed entirely within a hospital's secure network, PrivNurse AI guarantees patient data privacy (HIPAA/GDPR compliance) while delivering clinically-validated, explainable, and continuously improving AI assistance, directly at the point of care.

## The Training Pipeline: Forging a Clinical Expert

<img src="/assets/training_pipeline.png" alt="Trainging_Pipeline" style="zoom:85%;" />

This pipeline transforms the general-purpose Gemma 3n into a highly specialized clinical expert. All training is performed on-site to maintain data integrity.

#### **Step 1: Data Preprocessing**
We begin with anonymized medical records from our partner hospital. The data undergoes a rigorous preprocessing phase:
1.  **Data Cleaning:** Removing inconsistencies and artifacts.
2.  **Standardization:** Aligning terminology and units.
3.  **Data Integration:** Merging records from disparate sources (e.g., ER, inpatient).
4.  **Structure Information:** Identifying and tagging sections of the medical record.
5.  **Data De-identification:** A final, automated and human-verified pass to ensure all PHI is removed, adhering to HIPAA Safe Harbor guidelines.

#### **Step 2: Advanced Data Augmentation**
This is the core of our innovation. We create high-quality synthetic training data that teaches the model *how* to think, not just *what* to write.
*   **Medical Structured Chain-of-Thought (MedSCoT) for Task A:** Consultation note summarization is a high-complexity task that demands accurate identification of the *primary* consult reason amid extensive and often noisy patient history. Our approach leverages **Claude-Sonnet-4** as a “teacher model” to produce explicit, medically grounded reasoning chains.  

    **Example:**  
    > `<thinking>Task: Determine the primary reason for the Rehabilitation Medicine consult and formulate a concise summary. Although the patient was admitted for fever and bronchopneumonia, these conditions are less relevant to the consult. The key driver is swelling and pain on the left side of the neck, likely linked to a gymnastics-related sports injury. This musculoskeletal issue falls within Rehabilitation Medicine's scope and should be prioritized in the summary.</thinking>`  

    Integrating this structured reasoning into the training data enables the model to systematically filter irrelevant clinical details, maintain diagnostic focus, and deliver higher explainability in clinical NLP applications.

*   **Medical Data Distillation for Task B:** For discharge summaries, which require strict adherence to predefined medical documentation structure, we employ **MedGemma-27B-IT** as a teacher model. It is instructed to condense full patient records into summaries covering five essential elements: (1) Primary Diagnosis, (2) Lab/Exam Results, (3) Medications, (4) Consultations, and (5) Follow-up Plan. This structured distillation process produces high-fidelity datasets optimized for fine-tuning models in real-world clinical environments.

#### **Step 3: Parameter-Efficient Fine-Tuning (PEFT)**
We load the **Gemma-3n-E4B** base model and our augmented training dataset. The fine-tuning process is powered by cutting-edge tools for maximum efficiency:
*   **Unsloth:** We integrate the Unsloth library to significantly speed up training (up to 1.5x faster) and reduce VRAM usage by over 50%, making iterative fine-tuning highly practical.
*   **QLoRA (Quantized Low-Rank Adaptation):** We employ SFT (Supervised Fine-Tuning) with the QLoRA technique. This freezes the pretrained model weights and trains a small number of adaptable "LoRA" weights, drastically lowering the computational and memory requirements for training without sacrificing performance.

**Training Hyperparameters:**

| Hyperparameter | Expert Agent-A1 | Expert Agent-A2 | Expert Agent-B1 | Expert Agent-B2 |
| :--- | :--- | :--- | :--- | :--- |
| Base Model | unsloth/</br>gemma-3n-E4B-it | unsloth/</br>gemma-3n-E4B-it | unsloth/</br>gemma-3n-E4B-it | unsloth/</br>gemma-3n-E4B-it |
| LoRA `r` | `32` | `32` | `32` | `32` |
| LoRA `alpha`| `64` | `64` | `32` | `64` |
| LoRA Dropout | `0` | `0` | `0` | `0` | 
| Quantization Bits | `4-bit` | `4-bit` | `4-bit` | `4-bit` |
| Learning Rate| `1e-3` | `1e-3` | `2e-4` | `2e-4` |
| Total Batch Size | `96` | `96` | `32` | `32` |
| Epochs | `6` | `6` | `1` | `2` |
| Optimizer | `adamw_torch_fused`| `adamw_torch_fused`| `adamw_torch_fused`| `adamw_torch_fused` |
| Max Sequence Length | `8192` | `8192` | `32768` | `32768` |
| LR Scheduler Type | `linear` |`linear` |`linear` |`linear` |

#### **Step 4: Model Finalization for Deployment**
Once training is complete, the LoRA adapter is merged with the base model to create a full, fine-tuned model. To optimize for on-premises inference, we perform two final steps:
1.  **Format Conversion:** The model is converted from `safetensors` to the **GGUF (GPT-Generated Unified Format)**, which is highly optimized for fast loading and inference with frameworks like Ollama.
2.  **Quantization:** We use `llama.cpp` to create quantized versions of the model (e.g., Q8_0). This dramatically reduces the model's size and VRAM footprint, making it runnable on a wider range of hospital hardware, from dedicated servers to standard clinician workstations.


## The Application Pipeline: AI at the Clinician's Fingertips

<img src="/assets/application_pipeline.png" alt="Application_Pipeline" style="zoom:85%;" />

This pipeline is deployed on-site and handles real-time requests from users.





### **The Application Pipeline: AI at the Clinician's Fingertips**

This pipeline is deployed on-site and handles real-time requests from users.

#### **Task A & B: The Dual-Agent Inference System**
For summarization tasks, we utilize a sophisticated dual-agent architecture deployed on the **Ollama** framework. Ollama manages the local execution of our four fine-tuned GGUF models, dynamically loading and unloading them to efficiently manage VRAM.

1.  **Input Formatting:** For Task B (Discharge Summary), which involves time-sensitive data like lab reports and nursing notes, a `Temporal Data Processor` first sorts these records chronologically. All records are then passed to an `XML Formatter` that wraps the data in semantic tags (e.g., `<PhysicianDiagnosis>`, `<LabReport>`). This structured format helps the LLM better comprehend the complex medical data.
2.  **Agent Interaction:**
    *   **Agent 1 (The Summarizer):** First, `Nursing Record Summarization Model` (A1/B1) receives the formatted data and generates the clinical summary.
    *   **Agent 2 (The Highlighter):** The generated summary and the original source text are passed to the `Medical Record Key Highlighting Model` (A2/B2). This agent's sole purpose is to identify which keywords in the source text support the summary. It outputs its findings as a JSON object mapping summary sentences to source keywords.
3.  **Output Processing:** The `JSON Match Processor` uses this JSON to apply highlighting to the original medical record in the user interface. The final output presented to the clinician is the AI-generated summary alongside the source text with key evidence highlighted, providing immediate and intuitive explainability.

#### **Task C: Nursing Note Speech-to-Text**
To leverage Gemma 3n's native multimodal capabilities, which Ollama does not yet support for audio, we built a separate microservice.
*   **Unlocking Multimodality:** We run the `Nursing Voice Transcription Model` using the **Hugging Face Transformers** library. A **FastAPI** backend serves the model, providing a simple API endpoint for the front end.
*   **Prompt Engineering for Accuracy:** The backend is engineered with a specific system prompt to prime the model for the clinical context:
```
Please transcribe the provided audio into accurate written text. This is a medical/healthcare context where the speaker is a nursing professional.

## Instructions:
1. Convert the speech to text as accurately as possible
2. The speaker is a nurse, so expect medical terminology and nursing-related content
3. You may make minor adjustments to improve clarity and flow while maintaining the original meaning
4. Correct obvious speech errors, filler words, or unclear pronunciations to create a coherent transcript
5. Maintain professional medical language and terminology
6. Ensure the final transcript is readable and well-structured

## Output Requirements:
- Provide ONLY the clean, transcribed text
- Do not add commentary, explanations, or additional content
- Do not include timestamps or speaker labels
- Present the transcript as a flowing, coherent text document

Please transcribe the audio now.
```
*   **Workflow:** The frontend captures audio, sends it to the FastAPI endpoint, and displays the returned text. This simple but powerful feature liberates clinicians' hands and integrates seamlessly into their workflow.

#### **The Human-in-the-Loop: Confirmation and Feedback**
The user (Resident Physician, Nurse Practitioner, etc.) is always the final authority. They can:
*   **Confirm & Save:** Accept the AI's output, saving it directly to the Nursing Information System (NIS) or Hospital Information System (HIS).
*   **Correct & Improve:** Edit the AI-generated text. These corrections are invaluable. They are captured as high-quality, human-verified data and sent to a staging area for the **next round of iterative fine-tuning**. This closed-loop system ensures PrivNurse AI is constantly learning and improving, a critical feature for long-term clinical adoption.


# 🏥 PrivNurse Environment Setup and Installation Guide

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
