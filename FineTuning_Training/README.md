# 🔬 The Training Pipeline: Forging a Clinical Expert

<img src="/assets/training_pipeline.png" alt="Trainging_Pipeline" style="zoom:85%;" />

This pipeline transforms the general-purpose Gemma 3n into a highly specialized clinical expert. All training is performed on-site to maintain data integrity.

### **1. Parameter-Efficient Fine-Tuning (PEFT)**
We load the **Gemma-3n-E4B** base model and our augmented training dataset. The fine-tuning process is powered by cutting-edge tools for maximum efficiency:
*   **Unsloth:** We integrate the Unsloth library to significantly speed up training (up to 1.5x faster) and reduce VRAM usage by over 50%, making iterative fine-tuning highly practical.
*   **QLoRA (Quantized Low-Rank Adaptation):** We employ SFT (Supervised Fine-Tuning) with the QLoRA technique. This freezes the pretrained model weights and trains a small number of adaptable "LoRA" weights, drastically lowering the computational and memory requirements for training without sacrificing performance.

### **2. Model Finalization for Deployment**
Once training is complete, the LoRA adapter is merged with the base model to create a full, fine-tuned model. To optimize for on-premises inference, we perform two final steps:
1.  **Format Conversion:** The model is converted from `safetensors` to the **GGUF (GPT-Generated Unified Format)**, which is highly optimized for fast loading and inference with frameworks like Ollama.
2.  **Quantization:** We use `llama.cpp` to create quantized versions of the model (e.g., Q8_0). This dramatically reduces the model's size and VRAM footprint, making it runnable on a wider range of hospital hardware, from dedicated servers to standard clinician workstations.


# 🚀 Quich Start

Follow these steps to fine-tune and deploy the PrivNurse clinical expert models on your local system.

## Prerequisites

- Python 3.12 with Jupyter Notebook/Lab
- CUDA-compatible GPU (recommended: 16GB+ VRAM)
- [Ollama](https://ollama.com/) installed on your system
- Conda environment setup (see `environment_finetune.yml`)

## Step 1: Fine-tune the Models

Run the following Jupyter notebooks in sequence to train the four specialized clinical models:

### 1.1 Consultation Note Summary Model
```bash
jupyter notebook FineTuning_Gemma3n_PrivNurse_consult_summary.ipynb
```
**Output:** `gemma-3n-privnurse-consult-summary-v1.Q8_0.gguf`

### 1.2 Consultation Note Validation Model
```bash
jupyter notebook FineTuning_Gemma3n_PrivNurse_consult_validation.ipynb
```
**Output:** `gemma-3n-privnurse-consult-validation-v1_Q8_0.gguf`

### 1.3 Discharge Note Summary Model
```bash
jupyter notebook FineTuning_Gemma3n_PrivNurse_note_validation.ipynb
```
**Output:** `gemma-3n-privnurse-note-summary-v1_Q8_0.gguf`

### 1.4 Discharge Note Validation Model
```bash
jupyter notebook FineTuning_Gemma3n_PrivNurse_note_summary.ipynb
```
**Output:** `gemma-3n-privnurse-note-validation-v1_Q8_0.gguf`

> **Note:** Each notebook will automatically handle the complete training pipeline including data preprocessing, parameter-efficient fine-tuning (PEFT) with QLoRA, model merging, and GGUF conversion with Q8_0 quantization. Training time varies from 2-6 hours per model depending on your hardware configuration.

## Step 2: Import Models into Ollama

After all notebooks have completed successfully, import the trained models into Ollama using their corresponding Modelfiles:

### 2.1 Consultation Summary Model
```bash
ollama create gemma-3n-privnurse-consult-summary-v1 -f Modelfile_PrivNurse_Consultation_Summary_v1
```

### 2.2 Consultation Validation Model
```bash
ollama create gemma-3n-privnurse-consult-validation-v1 -f Modelfile_PrivNurse_Consultation_Validation_v1
```

### 2.3 Discharge Note Summary Model
```bash
ollama create gemma-3n-privnurse-note-summary-v1 -f Modelfile_PrivNurse_DischargeNote_Summary_v1
```

### 2.4 Discharge Note Validation Model
```bash
ollama create gemma-3n-privnurse-note-validation-v1 -f Modelfile_PrivNurse_DischargeNote_Validation_v1
```

## Step 3: Verify Model Installation

Check that all models are successfully imported:

```bash
ollama list
```

You should see all four PrivNurse models listed:
- `gemma-3n-privnurse-consult-summary-v1`
- `gemma-3n-privnurse-consult-validation-v1`
- `gemma-3n-privnurse-note-summary-v1`
- `gemma-3n-privnurse-note-validation-v1`

## Step 4: Test the Models

Run a quick test to ensure the models are working correctly:

```bash
# Test consultation summary model
ollama run gemma-3n-privnurse-consult-summary-v1 "Summarize the main reason for this endocrinology consultation..."

# Test discharge note validation model
ollama run gemma-3n-privnurse-note-validation-v1 "Please validate this discharge summary for completeness..."
```

## Troubleshooting

**GPU Memory Issues:**
- Reduce batch size in the notebook configurations
- Use gradient checkpointing if available
- Consider training models sequentially rather than in parallel

**GGUF Conversion Errors:**
- Ensure sufficient disk space (each model ~4-8GB)
- Verify that the training completed without errors
- Check that all required dependencies are installed

**Ollama Import Issues:**
- Confirm Ollama is running: `ollama serve`
- Verify GGUF files are in the correct directory
- Check Modelfile paths are accurate

## Next Steps

Once all models are successfully deployed, you can:
1. [Integrate them into the clinical application](https://github.com/weilin1205/PrivNurseAI/tree/main/privnurse_gemma3n)
2. [Set up API endpoints for audio model inference](https://github.com/weilin1205/PrivNurseAI/tree/main/ExpertAgentC_LLMServer_Nursing_Note_STT)