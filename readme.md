# Jupyter kernel for ProbLog
This is a simple [python wrapper kernel](https://jupyter-client.readthedocs.io/en/latest/wrapperkernels.html) for [ProbLog](https://dtai.cs.kuleuven.be/problog/).

## Installation
To add the kernel to your jupyter installation, run 

    jupyter kernelspec install --user problogkernel
    
(Note: You may need to `sudo`)

## Usage
See the [sample](/sample.ipynb) notebook for an overview of the features. See the [ProbLog tutorials](https://dtai.cs.kuleuven.be/problog/tutorial.html) for an introduction to problog.



( At the time of writing, cell-updates do not work as advertised off the [master-branch](https://github.com/ML-KULeuven/problog) of problog. Until the required changes can be integrated, they should be on either a fork of problog on my account, or on a branch that is likely named krishnan/usability or something similar. If it's not, get drop an email)
