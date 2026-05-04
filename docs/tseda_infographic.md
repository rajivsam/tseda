# tseda: Time Series Exploratory Data Analysis - Infographic

---

## **What is `tseda`?**

A simple, powerful tool for the exploratory data analysis (EDA) of your time series data.

---

## **Why EDA for Time Series?**

Unlock the potential of your data.

- **BUILD BETTER MODELS:** Understand variance for more accurate forecasts.
- **DISCOVER FEATURES:** Find predictive signals for classification tasks.
- **GAIN INSIGHTS:** Understand the fundamental structure of your data.

---

## **Core Features**

| Feature | Description |
| :--- | :--- |
| 📊 **Change Point Detection** | Automatically segment your time series into statistically distinct regimes. |
| 🧩 **Time Series Decomposition** | Use Singular Spectrum Analysis (SSA) to break down each segment into trend, seasonality, and noise. |
| 🧠 **Knowledge Integration** | Capture findings in a `kmds` knowledge base for collaborative, incremental analysis. |

---

## **How It Works: A 3-Step Workflow**

### **1. SEGMENT**
> The tool identifies significant **change points**, dividing the data into periods of consistent behavior.

**⬇**

### **2. DECOMPOSE**
> Within each segment, **Singular Spectrum Analysis (SSA)** separates the trend, seasonality, and other components.

**⬇**

### **3. SUMMARIZE & CAPTURE**
> Create clear descriptions of the findings, which are then stored in your `kmds` knowledge base.

---

## **Collaborate with `kmds`**

`tseda` + `kmds` = A powerful, shared understanding of your data.

- **Incremental Knowledge:** Build your knowledge base as you learn.
- **RAG-Ready:** Export data to power Retrieval Augmented Generation apps.

---

## **Getting Started in 3 Steps**

1.  **Setup KB Repo**
    ```bash
    # kmds uses git. Create or clone a repo for your knowledge base.
    ```
2.  **Install**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Launch**
    ```bash
    streamlit run src/user_interface/ts_analyze_ui.py
    ```
