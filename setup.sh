#!/bin/bash

# Load environment variables from .env file
load_env() {
    if [ -f .env ]; then
        set -a
        source .env
        set +a
    else
        if [ "$1" = "remote" ] || [ -z "$1" ]; then
            echo "Warning: .env file not found. Remote setup will be skipped."
            SKIP_REMOTE=true
            return 0
        fi
    fi
    
    # Validate required environment variables for remote setup
    if [ "$1" = "remote" ] || [ -z "$1" ]; then
        if [ -z "$REMOTE_HOST" ] || [ -z "$REMOTE_USER" ]; then
            if [ "$1" = "remote" ]; then
                echo "Error: REMOTE_HOST and REMOTE_USER must be set in .env file for remote setup"
                exit 1
            else
                echo "Warning: Remote configuration not found in .env file. Remote setup will be skipped."
                SKIP_REMOTE=true
                return 0
            fi
        fi
        
        # Set default SSH port if not specified
        REMOTE_PORT=${REMOTE_PORT:-22}
        
        # Construct remote connection string
        REMOTE_CONNECTION="$REMOTE_USER@$REMOTE_HOST"
        
        # Set SSH options for key-based auth only
        SSH_OPTS="-o BatchMode=yes -o PasswordAuthentication=no -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o ServerAliveInterval=30"
        SCP_OPTS="-o BatchMode=yes -o PasswordAuthentication=no -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
    fi
}

# Function to check system requirements
check_requirements() {
    echo "Checking system requirements..."
    
    # Check for curl
    if ! command -v curl &> /dev/null; then
        echo "Error: curl is required but not installed"
        exit 1
    fi
    
    # Check for ssh and scp for remote setup
    if [ "$1" = "remote" ] || [ -z "$1" ]; then
        if ! command -v ssh &> /dev/null || ! command -v scp &> /dev/null; then
            if [ "$1" = "remote" ]; then
                echo "Error: ssh and scp are required for remote setup but not installed"
                exit 1
            else
                echo "Warning: ssh and scp not found. Remote setup will be skipped."
                SKIP_REMOTE=true
                return 0
            fi
        fi
        
        # Check for SSH key
        if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
            echo "No SSH key found. Generating a new ED25519 key..."
            ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
            
            if [ $? -ne 0 ]; then
                echo "Error: Failed to generate SSH key"
                SKIP_REMOTE=true
                return 1
            fi
            
            echo "SSH key generated. Please add this public key to your remote server's authorized_keys:"
            cat ~/.ssh/id_ed25519.pub
            echo ""
            echo "You can add it to your remote server using:"
            echo "ssh-copy-id -i ~/.ssh/id_ed25519.pub $REMOTE_USER@$REMOTE_HOST"
            echo ""
            echo "After adding the key, run this script again."
            SKIP_REMOTE=true
            return 0
        fi
    fi
    
    # Check available disk space (minimum 2GB)
    available_space=$(df -P . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 2097152 ]; then  # 2GB in KB
        echo "Error: Insufficient disk space. At least 2GB required"
        exit 1
    fi
    
    echo "System requirements met"
}

# Function to check if Ollama is already installed
check_ollama() {
    if command -v ollama >/dev/null 2>&1; then
        echo "Ollama is already installed"
        return 0
    fi
    return 1
}

# Function to install Ollama
install_ollama() {
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Check if installation was successful
    if [ $? -eq 0 ]; then
        echo "Ollama installed successfully"
    else
        echo "Failed to install Ollama"
        exit 1
    fi
}

# Function to manage Ollama service
manage_ollama_service() {
    local max_retries=3
    local retry_count=0
    
    # Kill any existing Ollama processes
    if pgrep -x "ollama" > /dev/null; then
        echo "Stopping existing Ollama service..."
        pkill ollama
        sleep 2
    fi

    # Check if port 11434 is in use by another process
    while lsof -i:11434 > /dev/null 2>&1; do
        echo "Port 11434 is in use. Attempting to free it..."
        pkill -f "ollama"
        sleep 2
        
        ((retry_count++))
        if [ $retry_count -ge $max_retries ]; then
            echo "Error: Unable to free port 11434 after $max_retries attempts"
            echo "Please manually check what process is using port 11434:"
            echo "lsof -i:11434"
            exit 1
        fi
    done
    
    echo "Starting Ollama service..."
    ollama serve &
    sleep 5
    
    # Verify service is running
    if ! pgrep -x "ollama" > /dev/null; then
        echo "Error: Ollama service failed to start"
        exit 1
    fi
    
    # Verify port is accessible
    retry_count=0
    while ! curl -s http://localhost:11434/api/version >/dev/null 2>&1; do
        sleep 2
        ((retry_count++))
        if [ $retry_count -ge $max_retries ]; then
            echo "Error: Ollama service is not responding on port 11434"
            exit 1
        fi
        echo "Waiting for Ollama service to become responsive..."
    done
}

# Function to verify Ollama installation
verify_installation() {
    echo "Verifying Ollama installation..."
    if ! check_ollama; then
        echo "Error: Ollama installation verification failed"
        exit 1
    fi
    
    manage_ollama_service
    echo "Ollama installation verified successfully"
}

# Function for local setup
local_setup() {
    echo "Setting up Ollama locally..."
    
    if ! check_ollama; then
        install_ollama
    fi
    
    verify_installation
    
    # Pull the default model
    echo "Pulling the default coding model..."
    ollama pull codellama
    
    echo "Local setup completed successfully"
}

# Function for remote setup
remote_setup() {
    if [ "$SKIP_REMOTE" = true ]; then
        echo "Skipping remote setup due to missing requirements or configuration"
        return 0
    fi

    echo "Setting up Ollama on remote host: $REMOTE_CONNECTION (port: $REMOTE_PORT)"
    
    # Test SSH connection with timeout
    echo "Testing SSH connection..."
    if ! ssh $SSH_OPTS -p "$REMOTE_PORT" "$REMOTE_CONNECTION" "echo 'SSH connection successful'"; then
        echo "Error: Cannot connect to remote host. Please check:"
        echo "1. SSH key is properly added to remote host's authorized_keys"
        echo "2. Remote host is reachable"
        echo "3. Port $REMOTE_PORT is open"
        echo "4. Username $REMOTE_USER has access"
        return 1
    fi
    
    # Copy this script to remote host
    echo "Copying setup script to remote host..."
    scp $SCP_OPTS -P "$REMOTE_PORT" "$0" "$REMOTE_CONNECTION:/tmp/ollama_setup.sh"
    
    # Execute the script remotely for local setup
    echo "Running setup on remote host..."
    ssh $SSH_OPTS -p "$REMOTE_PORT" "$REMOTE_CONNECTION" "bash /tmp/ollama_setup.sh local && rm /tmp/ollama_setup.sh"
    
    echo "Remote setup completed successfully"
}

# Function to setup everything
setup_all() {
    echo "Starting Ollama setup..."
    
    # First setup locally
    local_setup
    
    # Then setup remotely if possible
    if [ "$SKIP_REMOTE" != true ]; then
        echo "Starting remote setup..."
        remote_setup
    fi
    
    echo "Setup process completed!"
}

# Main script execution
case "$1" in
    "local")
        check_requirements "local"
        load_env "local"
        local_setup
        ;;
    "remote")
        check_requirements "remote"
        load_env "remote"
        remote_setup
        ;;
    "")
        check_requirements
        load_env
        setup_all
        ;;
    *)
        echo "Usage: $0 [local|remote]"
        echo "Examples:"
        echo "  Complete setup:      $0"
        echo "  Local installation:  $0 local"
        echo "  Remote installation: $0 remote (uses settings from .env file)"
        exit 1
        ;;
esac

# Print success message
if [ "$1" = "remote" ] || ([ -z "$1" ] && [ "$SKIP_REMOTE" != true ]); then
    echo "
Setup completed successfully!
To use Ollama, you can:
1. Run 'ollama run codellama' to start a chat session
2. Use the API endpoint at http://localhost:11434
3. Connect to the remote instance at $REMOTE_HOST:11434

For remote access, make sure port 11434 is open on the remote machine.
"
else
    echo "
Setup completed successfully!
To use Ollama, you can:
1. Run 'ollama run codellama' to start a chat session
2. Use the API endpoint at http://localhost:11434
"
fi 