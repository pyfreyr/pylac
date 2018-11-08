# BAIDU 中文词法分析（LAC）

本文介绍从源码编译 CPU 版 PaddlePaddle 和 LAC，最终生成动态库使用 Python ctypes 调用。



## 1. 构建 paddle:dev 镜像

`paddle:dev` 用于后续编译 paddlepaddle 和 lac。

> 注意切换到 `v.0.14.0` 分支！！！

    $ git clone https://github.com/PaddlePaddle/Paddle.git paddle
    $ cd paddle
    $ git checkout v0.14.0

使用根目录内 Dockerfile 构建镜像：

    $ docker build -t paddle:dev --build-arg UBUNTU_MIRROR='http://mirrors.ustc.edu.cn/ubuntu/' .


## 2. 编译 paddle 基础库

这一步骤会产出 Paddle 的基础库，以及 python 版的 wheel 包。

    $ docker run -it -v $PWD:/paddle -w /paddle paddle:dev /bin/bash
    $ mkdir build
    $ cd build
    $ cmake -DCMAKE_BUILD_TYPE=Release -DWITH_AVX=ON -DWITH_MKL=ON -DWITH_MKLDNN=OFF -DWITH_GPU=OFF -DWITH_FLUID_ONLY=ON ..
    $ make -j 8

注意，这里关闭了 GPU 加速，启用 AVX/MKL 等加速环境。（按照官方 README 是没有 mkl 加速）

编译完成安装 whl：

    $ pip install python/dist/paddlepaddle-0.14.0-cp27-cp27mu-linux_x86_64.whl
    

## 3. 编译 fluid 预测库

Fluid 预测不包含在默认的官方镜像，以及默认的源码编译产出中。需要单独编译。

同样在 build 目录内执行：

    $ make -j 8 inference_lib_dist

完成后会在 `build/fluid_install_dir` 下产出 fluid 预测库，后面会使用的动态库为：

- fluid_install_dir/paddle/fluid/inference/libpaddle_fluid.so
- fluid_install_dir/third_party/install/mklml/lib/libmklml_intel.so
- fluid_install_dir/third_party/install/mklml/lib/libiomp5.so


完成后退出镜像。


## 4. 编译 lac

> 注意一定要切换到 `v1.0.0` 分支！！！

    $ git clone https://github.com/baidu/lac.git
    $ cd lac
    $ git checkout v1.0.0
    
如果系统没有安装 git lfs，conf 目录内文件只包含链接，实际的数据需要额外下载：

    $ curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.rpm.sh | bash
    $ yum install git-lfs
    $ git lfs install
    $ git lfs pull

如果网络问题需要多试几次才能安装成功。再次下载数据。

启动容器：

    $ cd ..
    $ docker run -it -v $PWD/paddle:/paddle -v $PWD:/lac paddle:dev /bin/bash

默认 lac 编译出来的是静态库，python 与 C 交互只能是动态库，所以修改 `/lac/CMakeLists.txt`：


    #add_library(lac ${SOURCE} include/ilac.h)
    add_library(lac SHARED ${SOURCE} include/ilac.h)
    #add_executable(lac_demo test/src/lac_demo.cpp)
    #target_link_libraries(lac_demo lac)
    #install(TARGETS lac DESTINATION ${PROJECT_SOURCE_DIR}/output/lib)
    #install(TARGETS lac_demo DESTINATION ${PROJECT_SOURCE_DIR}/output/demo)
    #install(FILES ${PROJECT_SOURCE_DIR}/include/ilac.h
    #        DESTINATION ${PROJECT_SOURCE_DIR}/output/include)


执行编译：

    $ cd /lac
    $ mkdir build
    $ cd build

    $ cmake -DPADDLE_ROOT=/paddle/build/fluid_install_dir ..
    $ make

完成后就能够在 `build` 目录下看到动态库 `liblac.so`。

退出容器。


至此，所有依赖的动态库已经编译完成，可以保存到任何目录。


## 5. Python 调用 C

Python 通过标准库的 ctypes 调用 C，使用参见官方文档：[ctypes — A foreign function library for Python](https://docs.python.org/3.6/library/ctypes.html)。

lac 对外的 C 接口位于 [include/ilac.h](https://github.com/baidu/lac/blob/master/include/ilac.h)，具体定义了 5 个函数和 1 个结构体：

```c
typedef struct TAG {
    int offset; /* byte offset in query */
    int length; /* byte length */
    char type[LAC_TYPE_MAX_LEN]; /* word type */
    double type_confidence; /* confidence of type */
} tag_t;

void* lac_create(const char* conf_dir);
void lac_destroy(void* lac_handle);
void* lac_buff_create(void* lac_handle);
void lac_buff_destroy(void* lac_handle, void* lac_buff);
int lac_tagging(void* lac_handle, void* lac_buff,
    const char* query, tag_t* results, int max_result_num);
```

通过 ctypes 加载动态库 `liblac.so` 即可调用原生 C 接口，对 lac 的使用参照 [test/src/lac_demo.cpp](https://github.com/baidu/lac/blob/master/test/src/lac_demo.cpp) 实现了 python 版本的 `init_dict`, `destroy_dict` 和 `tagging` 函数，源码参见 [pylac/tag](pylac/tag.py)。

> 这里的 Python 实现删除了 `tagging` 多线程的处理部分。


现在将编译好的 paddle_fluid, mkl, lac 动态库加入环境变量即可运行：

    $ export LD_LIBRARY_PATH=/lac/lib
    $ python tag.py
    
> 如果编译时没有加入 MKL 加速，运行速度会慢很多。

## 6. RESTful API

使用 tornado 启动服务见 [lac_server.py](lac_server.py)，构建 lac 镜像见 [Dockerfile](Dockerfile)。


启动镜像：

    $ docker run -d --name lac -p 8888:8888 lac:1.0.0

> 注意：动态库编译使用了 MKL 和 AVX，请确保镜像运行在支持的服务器上。


访问服务：

- URL

        http://10.202.81.187:8888/v1/lac/word

- Request

        {
            "text": "我爱北京天安门。"
        }
    
- Response
 
        {
            "words": [
                {
                    "length": 3, 
                    "type": "r", 
                    "name": "我", 
                    "offset": 0
                }, 
                {
                    "length": 3, 
                    "type": "v", 
                    "name": "爱", 
                    "offset": 3
                }, 
                {
                    "length": 15, 
                    "type": "LOC", 
                    "name": "北京天安门", 
                    "offset": 6
                }, 
                {
                    "length": 3, 
                    "type": "w", 
                    "name": "。", 
                    "offset": 21
                }
            ], 
            "success": true
        }


## CHANGELOG

### 2018-10-23 10:20:28
- 分词结果输出格式由 tab 分隔的字符串改为 dict

### 2018-10-23 10:02:07
- 动态库 lib 和模型数据 conf 上传至[网盘](http://10.202.81.90:8080/apps/files/?dir=/baidu-lac&fileid=670)，另备份地址 [lac 模型和动态库](https://gitlab.gridsum.com/chenfei/baidu-lac/issues/3#note_526232)