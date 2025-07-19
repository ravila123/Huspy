# SSH Setup Guide for Blue Rover

This guide explains how to configure secure SSH access for remote control of your Blue Rover system.

## Quick Setup

Run the automated SSH setup script:

```bash
# Basic setup with default settings
./scripts/setup_ssh.sh

# Setup with custom port and fail2ban
./scripts/setup_ssh.sh --port 2222 --fail2ban
```

## Manual Setup Steps

If you prefer to configure SSH manually, follow these steps:

### 1. Generate SSH Key Pair (on your local machine)

```bash
# Generate Ed25519 key (recommended)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Or generate RSA key (alternative)
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"
```

### 2. Copy Public Key to Raspberry Pi

```bash
# Method 1: Using ssh-copy-id (easiest)
ssh-copy-id pi@your-pi-ip-address

# Method 2: Manual copy
cat ~/.ssh/id_ed25519.pub | ssh pi@your-pi-ip-address "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 3. Configure SSH Daemon

Edit the SSH configuration file:

```bash
sudo nano /etc/ssh/sshd_config
```

Apply these security settings:

```
# Enable key-based authentication
PubkeyAuthentication yes

# Disable password authentication
PasswordAuthentication no

# Disable root login
PermitRootLogin no

# Additional security
PermitEmptyPasswords no
ChallengeResponseAuthentication no
Protocol 2
```

### 4. Restart SSH Service

```bash
sudo systemctl restart ssh
```

## Security Hardening Options

### Custom SSH Port

Change the default SSH port (22) to reduce automated attacks:

```bash
# In /etc/ssh/sshd_config
Port 2222
```

Connect using custom port:
```bash
ssh -p 2222 pi@your-pi-ip-address
```

### Fail2Ban Protection

Install fail2ban to protect against brute force attacks:

```bash
sudo apt-get install fail2ban
```

Create `/etc/fail2ban/jail.local`:

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
```

Enable fail2ban:
```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Additional Security Measures

1. **Limit User Access**:
   ```
   AllowUsers your-username
   DenyUsers root
   ```

2. **Connection Limits**:
   ```
   MaxAuthTries 3
   MaxSessions 2
   ClientAliveInterval 300
   ClientAliveCountMax 2
   ```

3. **Disable Unused Features**:
   ```
   X11Forwarding no
   AllowTcpForwarding no
   GatewayPorts no
   ```

## Testing SSH Configuration

### Test Configuration Syntax

```bash
sudo sshd -t
```

### Test Connection

Before closing your current session, test SSH access in a new terminal:

```bash
ssh pi@your-pi-ip-address
```

If using a custom port:
```bash
ssh -p 2222 pi@your-pi-ip-address
```

## Troubleshooting

### Cannot Connect After Configuration

1. **Check SSH service status**:
   ```bash
   sudo systemctl status ssh
   ```

2. **Check SSH logs**:
   ```bash
   sudo journalctl -u ssh -f
   ```

3. **Restore backup configuration**:
   ```bash
   sudo cp /etc/ssh/sshd_config.backup.* /etc/ssh/sshd_config
   sudo systemctl restart ssh
   ```

### Permission Issues

Ensure correct permissions on SSH files:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

### Key Authentication Not Working

1. **Check authorized_keys format**:
   - Each key should be on a single line
   - No extra spaces or line breaks
   - Correct key type prefix (ssh-ed25519, ssh-rsa, etc.)

2. **Verify SSH agent**:
   ```bash
   ssh-add -l
   ssh-add ~/.ssh/id_ed25519
   ```

3. **Debug connection**:
   ```bash
   ssh -v pi@your-pi-ip-address
   ```

## Remote Access Best Practices

### Network Security

1. **Use VPN**: Set up a VPN for secure remote access
2. **Firewall Rules**: Configure UFW or iptables to limit SSH access
3. **Dynamic DNS**: Use services like DuckDNS for dynamic IP addresses

### Connection Management

1. **SSH Config File**: Create `~/.ssh/config` on your local machine:
   ```
   Host blue-rover
       HostName your-pi-ip-address
       User pi
       Port 2222
       IdentityFile ~/.ssh/id_ed25519
   ```

2. **Connection Shortcuts**:
   ```bash
   ssh blue-rover
   ```

### Monitoring and Maintenance

1. **Monitor SSH logs**:
   ```bash
   sudo tail -f /var/log/auth.log
   ```

2. **Check fail2ban status**:
   ```bash
   sudo fail2ban-client status sshd
   ```

3. **Regular key rotation**: Update SSH keys periodically

## Integration with Blue Rover

Once SSH is configured, you can remotely control your Blue Rover:

```bash
# Connect to Pi
ssh pi@your-pi-ip-address

# Run Blue Rover in different modes
./run_rover.sh ps5      # PS5 controller mode
./run_rover.sh manual   # Keyboard control
./run_rover.sh monitor  # Battery monitoring
./run_rover.sh web      # Web interface
```

## Security Checklist

- [ ] SSH keys generated and copied
- [ ] Password authentication disabled
- [ ] Root login disabled
- [ ] Custom SSH port configured (optional)
- [ ] fail2ban installed and configured (optional)
- [ ] SSH configuration tested
- [ ] Backup of original SSH config created
- [ ] Firewall rules configured
- [ ] SSH access tested from remote location

## Support

If you encounter issues with SSH setup:

1. Check the troubleshooting section above
2. Review SSH logs for error messages
3. Ensure your network allows SSH connections
4. Verify firewall settings on both local and remote machines

For Blue Rover specific issues, refer to the main troubleshooting guide.