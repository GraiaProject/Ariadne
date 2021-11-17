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

### 在 Linux 上安装 Docker Compose

Linux 发行版软件源中一般有, 不过可能版本较旧; 可以参照[官方文档](https://docs.docker.com/compose/install/)安装最新版本.

## 使用 Docker 安装 Mirai 与 mirai-api-http

### 目录准备

Mirai 将登录信息, 还有 Mirai 与 mirai-api-http 的配置文件, 保存在 `bots` 与 `config` 文件夹中.

在镜像中, 这两个文件夹分别位于 `/app/bots` 与 `/app/config` 中.

建议将 Mirai 的保存到容器外部.

新建文件夹:

```bash
mkdir mirai
mkdir mirai/bots
mkdir mirai/config
```

### 使用 Docker 运行

在刚刚建立的 `mirai` 目录中, 运行:

```bash
docker run \
    --name mirai \
    -v "$PWD"/bots:/app/bots \
    -v "$PWD"/config:/app/config \
    -p 8080:8080 \
    -it \
    zhaozuohong/mah
```

### 使用 Docker Compose 运行

将以下内容保存到 `mirai/docker-compose.yml` 文件中:

```yml
version: "3"

services:
  mirai:
    image: zhaozuohong/mah
    container_name: mirai
    stdin_open: true
    tty: true
    volumes:
      - ./bots:/app/bots
      - ./config:/app/config
    ports:
      - "8080:8080"
```

随后使用 `docker-compose up -d` 运行.

### 设置 mirai-api-http

mirai-api-http 的设置文件在 `mirai/config/net.mamoe.mirai-api-http/settings.yml` .

注意 `adapterSettings` 下的设置, 是 `mirai-api-http` 在容器中的网络设置. 因此, `host` 应该写 `0.0.0.0`, 端口保持 `8080` 即可.

如果想让 mirai-api-http 绑定其它端口在 `8080` 以外的端口运行, 不需要修改 mirai-api-http 的端口设置, 只要修改 Docker 命令或者 `docker-compose.yml` 文件即可.

例如, 在 `3000` 端口运行:

```bash
docker run \
    --name mirai \
    -v "$PWD"/bots:/app/bots \
    -v "$PWD"/config:/app/config \
    -p 3000:8080 \
    -it \
    zhaozuohong/mah
```

或使用 Docker Compose:

```yml
version: "3"

services:
  mirai:
    image: zhaozuohong/mah
    container_name: mirai
    stdin_open: true
    tty: true
    volumes:
      - ./bots:/app/bots
      - ./config:/app/config
    ports:
      - "3000:8080"
```

## 容器相关的操作

连按 `Ctrl-P` `Ctrl-Q`, 将容器转为后台运行. 可通过 `docker logs mirai` 查看输出, 或使用 `docker attach mirai` 再次连接容器.
