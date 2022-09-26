# test docker for manjaro desktop
FROM manjarolinux/base:latest

# Update the repositories & Install openssh
RUN pacman -Syy && pacman -S --noconfirm openssh
# Generate ssh host keys of all types
RUN ssh-keygen -A
# Add password for root
RUN echo "root:root" | chpasswd
# Expose tcp port
EXPOSE 22
# Add a sudoer
RUN USER_NAME=test && \
    useradd --create-home --shell /bin/bash $USER_NAME && \
    echo "$USER_NAME:$USER_NAME" | chpasswd && \
    echo "$USER_NAME ALL=(ALL) ALL" >> /etc/sudoers
# Install packages
RUN pacman -S --noconfirm vi
RUN pacman -S --noconfirm sysvinit-tools
RUN pacman -S --noconfirm python-pip
# Run openssh daemon
CMD ["/usr/sbin/sshd", "-D"]