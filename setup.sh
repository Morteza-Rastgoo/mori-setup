#!/bin/bash

echo "Setting up MoriCodingAgent..."

# Create config directory
mkdir -p ~/.mori

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
echo "Checking Python version..."
if ! command_exists python3; then
    echo "Error: Python 3 is required but not installed"
    exit 1
fi

# Install required packages
echo "Installing required packages..."
python3 -m pip install -r requirements.txt

# Function to get CPU info
get_cpu_info() {
    local CPU_SCORE=0
    local CPU_CORES=0
    local CPU_MODEL=""
    local CPU_SPEED=0
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        CPU_CORES=$(sysctl -n hw.ncpu)
        CPU_MODEL=$(sysctl -n machdep.cpu.brand_string)
        # On Apple Silicon, use a different approach
        if [[ "$CPU_MODEL" == *"Apple"* ]]; then
            # Assign a high score for Apple Silicon
            CPU_SCORE=20  # M1/M2 chips are very capable
        else
            CPU_SPEED=$(sysctl -n hw.cpufrequency_max)
            CPU_SPEED=$((CPU_SPEED / 1000000)) # Convert to MHz
            CPU_SCORE=$((CPU_CORES * CPU_SPEED / 1000))
        fi
    else
        # Linux
        CPU_CORES=$(nproc)
        CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -n1 | cut -d':' -f2 | xargs)
        CPU_SPEED=$(grep "cpu MHz" /proc/cpuinfo | head -n1 | cut -d':' -f2 | xargs | cut -d'.' -f1)
        CPU_SCORE=$((CPU_CORES * CPU_SPEED / 1000))
    fi
    
    # Print info
    {
        echo "CPU_MODEL=$CPU_MODEL"
        echo "CPU_CORES=$CPU_CORES"
        if [[ "$CPU_MODEL" != *"Apple"* ]]; then
            echo "CPU_SPEED=$CPU_SPEED"
        fi
        echo "CPU_SCORE=$CPU_SCORE"
    } > ~/.mori/cpu_info.txt
    
    echo "$CPU_SCORE"
}

# Function to get memory info
get_memory_info() {
    local MEM_SCORE=0
    local TOTAL_MEM=0
    local FREE_MEM=0
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        TOTAL_MEM=$(sysctl -n hw.memsize)
        TOTAL_MEM=$((TOTAL_MEM / 1024 / 1024)) # Convert to MB
        # For macOS, use a percentage of total memory as score
        MEM_SCORE=$((TOTAL_MEM / 1024))  # Convert to GB for score
    else
        # Linux
        TOTAL_MEM=$(free -m | awk '/Mem:/ {print $2}')
        FREE_MEM=$(free -m | awk '/Mem:/ {print $4}')
        MEM_SCORE=$((FREE_MEM / 1024))
    fi
    
    # Print info
    {
        echo "TOTAL_MEM=$TOTAL_MEM"
        if [[ "$(uname)" != "Darwin" ]]; then
            echo "FREE_MEM=$FREE_MEM"
        fi
        echo "MEM_SCORE=$MEM_SCORE"
    } > ~/.mori/mem_info.txt
    
    echo "$MEM_SCORE"
}

# Function to check GPU availability
check_gpu() {
    local GPU_TYPE=0
    local GPU_INFO=""
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # Check for Metal support on macOS
        if system_profiler SPDisplaysDataType | grep -q "Metal"; then
            GPU_INFO=$(system_profiler SPDisplaysDataType | grep "Chipset Model" | cut -d':' -f2 | xargs)
            echo "GPU: $GPU_INFO (Metal supported)"
            GPU_TYPE=1
        fi
    else
        # Check for NVIDIA GPU on Linux
        if command_exists nvidia-smi; then
            GPU_INFO=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader)
            echo "GPU: $GPU_INFO"
            GPU_TYPE=2
        fi
    fi
    
    # Print info
    {
        echo "GPU_INFO=$GPU_INFO"
        echo "GPU_TYPE=$GPU_TYPE"
    } > ~/.mori/gpu_info.txt
    
    echo "$GPU_TYPE"
}

# Function to determine optimal model based on system capabilities
determine_optimal_model() {
    local CPU_SCORE=$1
    local MEM_SCORE=$2
    local GPU_TYPE=$3
    
    # Print system info
    echo "System Scores:"
    if [ -f ~/.mori/cpu_info.txt ]; then
        cat ~/.mori/cpu_info.txt
    fi
    if [ -f ~/.mori/mem_info.txt ]; then
        cat ~/.mori/mem_info.txt
    fi
    if [ -f ~/.mori/gpu_info.txt ]; then
        cat ~/.mori/gpu_info.txt
    fi
    
    local BEST_MODEL=""
    
    # For Apple Silicon, prefer the most capable model
    if [[ "$(uname)" == "Darwin" ]] && [[ "$(sysctl -n machdep.cpu.brand_string)" == *"Apple"* ]]; then
        BEST_MODEL="codellama:7b-instruct-q4_K_M"
    else
        # Select model based on available resources
        if [ "$CPU_SCORE" -ge 8 ] && [ "$MEM_SCORE" -ge 16 ]; then
            BEST_MODEL="codellama:7b-instruct-q4_K_M"
        elif [ "$CPU_SCORE" -ge 6 ] && [ "$MEM_SCORE" -ge 12 ]; then
            BEST_MODEL="llama2:7b-chat-q4_K_M"
        else
            BEST_MODEL="mistral:7b-instruct-q4_K_M"
        fi
    fi
    
    echo "Selected model: $BEST_MODEL"
    echo "$BEST_MODEL" > ~/.mori/optimal_model.txt
    
    # Save complete system info
    {
        echo "# System Information"
        echo "TIMESTAMP=$(date +%s)"
        echo ""
        echo "# CPU Information"
        cat ~/.mori/cpu_info.txt
        echo ""
        echo "# Memory Information"
        cat ~/.mori/mem_info.txt
        echo ""
        echo "# GPU Information"
        cat ~/.mori/gpu_info.txt
        echo ""
        echo "# Selected Model"
        echo "OPTIMAL_MODEL=$BEST_MODEL"
    } > ~/.mori/system_info.txt
}

# Run system analysis
echo "Analyzing system capabilities..."
CPU_SCORE=$(get_cpu_info)
MEM_SCORE=$(get_memory_info)
check_gpu
GPU_TYPE=$?

# Determine optimal model
determine_optimal_model "$CPU_SCORE" "$MEM_SCORE" "$GPU_TYPE"

# Create or update .env file with optimal settings
if [ -f .env ]; then
    # Backup existing .env
    cp .env .env.backup
fi

OPTIMAL_MODEL=$(cat ~/.mori/optimal_model.txt)

# Update .env file
cat > .env << EOL
# Remote server configuration
REMOTE_HOST="${REMOTE_HOST:-localhost}"
REMOTE_USER="${REMOTE_USER:-$USER}"
REMOTE_PORT="${REMOTE_PORT:-22}"

# Ollama configuration
OLLAMA_HOST="${OLLAMA_HOST:-localhost}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_MODEL="$OPTIMAL_MODEL"
OLLAMA_REMOTE="${OLLAMA_REMOTE:-false}"

# Agent configuration
DEFAULT_ITERATIONS="${DEFAULT_ITERATIONS:-25}"
EOL

echo "Setup complete! Optimal model selected: $OPTIMAL_MODEL" 