FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

USER root

# Remove Yarn repository to avoid GPG key expiry issues
# Yarn is not needed for this Python/Lambda project
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && rm -f /usr/share/keyrings/yarn.gpg \
    && apt-get update
