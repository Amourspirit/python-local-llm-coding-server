import subprocess
import sys

def start_mlx_server():
    # Constructing the command as a list of arguments
    command = [
        sys.executable, "-m", "mlx_vlm.server",
        "--model", "mlx-community/gemma-4-31b-it-8bit",
        "--port", "8066",
        "--kv-bits", "3.5",
        "--kv-quant-scheme", "turboquant"
    ]

    print(f"🚀 Starting MLX VLM Server on port 8066...")
    
    try:
        # run() waits for the process to complete. 
        # If you want it to run in the background, use subprocess.Popen()
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user.")

if __name__ == "__main__":
    start_mlx_server()
