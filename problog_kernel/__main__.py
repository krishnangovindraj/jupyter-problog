if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    from .pblkernel import ProblogKernel
    IPKernelApp.launch_instance(kernel_class=ProblogKernel)
