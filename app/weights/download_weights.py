import os
import kagglehub
import urllib.request

def main() -> None:
    # Override default weight local cache directory
    weight_dir = os.environ["KAGGLEHUB_CACHE"] = os.path.join(os.path.dirname(__file__), "")
    print("Weights will be stored in:", weight_dir)
    
    # Download latest version
    speciesnet_path = kagglehub.model_download("google/speciesnet/pyTorch/v4.0.2b")
    megadetector_path = urllib.request.urlretrieve("https://github.com/agentmorris/MegaDetector/releases/download/v5.0/md_v5a.0.0.pt", weight_dir + "models/megadetector_v5a.0.0.pt")

    print("Path to sepciesnet model files:", speciesnet_path)
    print("Path to megadetector model files:", megadetector_path)


if __name__ == "__main__":
    main()
