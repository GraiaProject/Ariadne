# 使用 Docker 安装 Mirai

## Docker 的安装与基本配置

### Windows 与 macOS

下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop).

### Linux

既可以使用发行版软件源中的版本, 也可参照[官方文档](https://docs.docker.com/engine/install/)安装最新版本.

### 换源

如果直接下载有困难, 可以换用国内的源, 如:

- [https://help.aliyun.com/document_detail/60750.html](https://help.aliyun.com/document_detail/60750.html)
- [http://mirrors.ustc.edu.cn/help/dockerhub.html](http://mirrors.ustc.edu.cn/help/dockerhub.html)

## 使用 Docker 安装 Mirai 与 mirai-api-http

### Docker 镜像

构建镜像所用 Dockerfile 在 [https://github.com/ZhaoZuohong/mirai-mah-docker](https://github.com/ZhaoZuohong/mirai-mah-docker).

### 运行 Mirai

```bash
docker run \
    --name mirai \
    --restart=always \
    -it \
    -p <主机端口号>:8080 \
    -e VERIFY_KEY=<mirai-api-http的密钥> \
    zhaozuohong/mah
```

容器启动时会运行 `mcl` . 此时可以输入命令, 如 `login` 以进行登录.

### 使用已有的登录信息

如果想要使用已有的登录信息, 可将存储登录信息的文件夹挂载到容器中:

```bash
docker run \
    -v <你的bots文件夹>:/app/bots \
    --name mirai \
    --restart=always \
    -it \
    -p <主机端口号>:8080 \
    -e VERIFY_KEY=<mirai-api-http的密钥> \
    zhaozuohong/mah
```

### 相关操作

连按 `Ctrl-P` `Ctrl-Q`, 可将容器转为后台运行. 可通过 `docker logs mirai` 查看输出, 或使用 `docker attach mirai` 再次连接容器.
