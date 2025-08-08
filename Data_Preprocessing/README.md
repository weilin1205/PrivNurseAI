# PrivNurse Data Preprocessing

## ✨ Abstract
The preprocessing stage implements comprehensive data cleaning and standardization procedures:

* **Data Cleaning**: Removal of incomplete records to ensure data integrity and prevent downstream processing errors.
* **Data Integration**: Consolidation of multi-source medical records from different hospital departments and systems, ensuring temporal consistency and data completeness
* **Standardization**: Implementation of uniform formatting across different record types, including consistent date formats, medication dosing notation, and laboratory value representations
* **Structure Information**: Extraction and organization of key clinical data points using natural language processing techniques specifically designed for medical text
* **Data De-identification**: Removal of all personally identifiable information (PII), such as patient names, identification numbers, and contact details, to ensure data is fully de-identified and compliant with privacy regulations.

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/weilin1205/PrivNurseAI.git
cd PrivNurseAI/Data_Preprocessing
```
### 2. Install dependencies
```bash
pip install rich psutil
```

### 3. Run Data Preprocessing Script
```bash
python PrivNurse_data_preprocessing.py
```

## 🌟 Result

![Nursing Note STT Demo](/assets/data_preprocessing.jpg)