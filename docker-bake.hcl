group "default" {
  targets = ["app"]
}

target "app" {
  context = "."
  dockerfile = "Dockerfile"
  tags = ["mundi-public:local"]
  args = {
    VITE_WEBSITE_DOMAIN = "http://localhost:8000"
    NODE_IMAGE          = "mirror.gcr.io/library/node:20-bookworm-slim"
    APT_MIRROR          = "https://mirrors.tuna.tsinghua.edu.cn/debian"
  }
}