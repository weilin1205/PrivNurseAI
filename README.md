# PrivNurse AI: Revolutionizing Clinical Documentation with On-Device Intelligence
> Empowering Healthcare Professionals with Secure, Offline-Ready AI that Transforms Medical Documentation While Keeping Patient Data Protected

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
*   **Medical Structured Chain-of-Thought (MedSCoT) for Task A:** Summarizing consultation notes is the most challenging task, requiring the model to identify the single most urgent reason for the consult amidst extensive patient history. We use **Claude-Sonnet-4** as a "teacher model" to generate step-by-step reasoning paths. For example:
    > `<thinking>Analysis: Although the patient was admitted for post-operative management of a bone fracture, the main reason for the endocrinology consultation was the acute hyperglycemia control. I must prioritize this in the summary.</thinking>`
    This explicit reasoning chain, included in the training data, dramatically improves the model's ability to filter clinical noise and enhances its explainability.

*   **Medical Data Distillation for Task B:** For discharge summaries, which require adherence to a specific structure, we use **MedGemma-27B-IT** as a teacher model. We prompt it to distill full patient histories into summaries covering five key areas: (1) Primary Diagnosis, (2) Lab/Exam Results, (3) Medications, (4) Consultations, and (5) Follow-up Plan. This structured distillation creates a robust dataset for fine-tuning.

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
