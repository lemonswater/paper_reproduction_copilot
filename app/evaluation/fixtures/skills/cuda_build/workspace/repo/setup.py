from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CUDAExtension, CUDA_HOME


setup(
    name="fixture_extension",
    ext_modules=[
        CUDAExtension(
            name="fixture_extension",
            sources=["extension.cpp", "kernel.cu"],
        )
    ],
    cmdclass={"build_ext": BuildExtension},
)

assert CUDA_HOME is not None
