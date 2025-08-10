# 🔮 Advanced Data Augmentation and Distillation

This is the core of our innovation. We create high-quality synthetic training data that teaches the model *how* to think, not just *what* to write.

*   **Medical Structured Chain-of-Thought (MedSCoT) for Task A:** Consultation note summarization is a high-complexity task that demands accurate identification of the *primary* consult reason amid extensive and often noisy patient history. Our approach leverages **Claude-Sonnet-4** as a "teacher model" to produce explicit, medically grounded reasoning chains.  

    **Example:**  
    > `<thinking>Task: Determine the primary reason for the Rehabilitation Medicine consult and formulate a concise summary. Although the patient was admitted for fever and bronchopneumonia, these conditions are less relevant to the consult. The key driver is swelling and pain on the left side of the neck, likely linked to a gymnastics-related sports injury. This musculoskeletal issue falls within Rehabilitation Medicine's scope and should be prioritized in the summary.</thinking>`  

    Integrating this structured reasoning into the training data enables the model to systematically filter irrelevant clinical details, maintain diagnostic focus, and deliver higher explainability in clinical NLP applications.

*   **Medical Data Distillation for Task B:** For discharge summaries, which require strict adherence to predefined medical documentation structure, we employ **MedGemma-27B-IT** as a teacher model. It is instructed to condense full patient records into summaries covering five essential elements: (1) Primary Diagnosis, (2) Lab/Exam Results, (3) Medications, (4) Consultations, and (5) Follow-up Plan. This structured distillation process produces high-fidelity datasets optimized for fine-tuning models in real-world clinical environments.

# 🚀 Quick Start

Follow these steps to prepare training datasets and fine-tune the PrivNurse clinical expert models on your local system.

## Step 1: Generate Training Datasets

Before fine-tuning the models, you need to generate the specialized training datasets using our advanced data augmentation and distillation techniques.

### 1.1 Consultation Note Datasets (Claude-Generated)
Generate training data for consultation note tasks using Claude-Sonnet-4's structured reasoning:

```bash
# Consultation validation dataset
python privNurse_consult_validation_claude.py

# Consultation summary dataset  
python privNurse_consult_summary_claude.py
```

### 1.2 Discharge Note Datasets (MedGemma-Generated)
Generate training data for discharge note tasks using MedGemma-27B-IT distillation:

```bash
# Discharge note validation dataset
jupyter notebook PrivNurse_note_validation_medgemma.ipynb

# Discharge note summary dataset
jupyter notebook PrivNurse_note_summary_medgemma.ipynb
```

**Expected Outputs:**
- `Datasets-consult-summary.csv` - Consultation summary training data
- `Datasets-consult-validation.csv` - Consultation validation training data
- `Datasets-note-summary.csv` - Discharge note summary training data
- `Datasets-note-validation.csv` - Discharge note validation training data

> **Note:** The dataset generation process leverages teacher models to create high-quality Chain-of-Thought reasoning patterns and structured medical distillation, ensuring the training data teaches both clinical accuracy and systematic thinking processes.

# Next Steps

Once your training datasets are ready, proceed to the [model fine-tuning section](https://github.com/weilin1205/PrivNurseAI/tree/main/FineTuning_Training) to train the four specialized clinical models using the generated datasets. Each model will be trained on its corresponding dataset to achieve optimal performance for specific clinical documentation tasks.