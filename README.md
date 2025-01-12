# Powerline

### 1. Installation
There are two ways to install the dependencies for your project: Pipenv or requirements.txt. Below are the installation steps for both approaches.

**Using Pipenv and Pipfile**
If you want to use Pipenv, which manages your virtual environment and dependencies in a Pipfile and Pipfile.lock, follow these steps:

Install Pipenv (if not already installed):

```bash
pip install pipenv
```

Clone the repository:

```bash
git clone https://github.com/yourusername/Powerline.git
```

Navigate to the project directory:

```bash
cd your-repo
```

Install dependencies using Pipenv:

```bash
pipenv install
```
This will install all the required packages listed in the Pipfile.

Activate the virtual environment:

```bash
pipenv shell
```


**Using requirements.txt**
If you prefer to use a simple requirements.txt file follow these steps:

```bash
pip install -r requirements.txt
```
This will install all the necessary packages specified in requirements.txt.


To run the analysis and see the results, open `analysis.ipynb` notebook. This notebook uses modules under `src` folder. All the logics for calculations are inside `functions.py` and all the plottings are inside `plotter.py`.


The following is the structure of this repo. 
C:.
│   analysis.ipynb
│   Pipfile
│   Pipfile.lock
│   Powerline.code-workspace
│   README.md
│   requirements.txt
│
├───materials
│       NEM Registration and Exemption List.xlsx
│       Powerline Takehome - Energy Analyst.pdf
│       raw_bid_data_2024-06-13.xlsx
│
└───src
        functions.py
        plotter.py