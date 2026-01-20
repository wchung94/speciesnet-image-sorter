import os
from glob import glob
import kagglehub
import urllib.request

def main() -> None:
    # Override default weight local cache directory
    weight_dir = os.environ["KAGGLEHUB_CACHE"] = os.path.join(os.path.dirname(__file__), "")
    print("Weights will be stored in:", weight_dir)
    

    # Recursive search for pt files to check if they already exist
    result = [y for x in os.walk(weight_dir) for y in glob(os.path.join(x[0], '*.pt'))]
    print(result)

    


    if not os.path.exists(weight_dir + "models/speciesnet.pt"):
        # Download latest version
        speciesnet_path = kagglehub.model_download("google/speciesnet/pyTorch/v4.0.2b", path="full_image_88545560_22x8_v12_epoch_00153.pt")
        os.rename(speciesnet_path, weight_dir + "models/speciesnet.pt")
        os.environ["SPECIESNET_WEIGHTS_PATH"] = speciesnet_path
        print("Path to speciesnet model files:", speciesnet_path)
    else:
        print("Speciesnet Model files already exist: " + weight_dir + "models/speciesnet.pt")
        os.environ["SPECIESNET_WEIGHTS_PATH"] = weight_dir + "models/speciesnet.pt"
    if not os.path.exists(weight_dir + "models/megadetector.pt"):
        megadetector_path = urllib.request.urlretrieve("https://github.com/agentmorris/MegaDetector/releases/download/v5.0/md_v5a.0.0.pt", weight_dir + "models/megadetector.pt")
        os.environ["MEGADETECTOR_WEIGHTS_PATH"] = megadetector_path
        print("Path to megadetector model files:", megadetector_path)
    else:
        print("MegaDetector Model already exist: " + weight_dir + "models/megadetector.pt")
        os.environ["SPECIESNET_WEIGHTS_PATH"] = weight_dir + "models/megadetector.pt"

if __name__ == "__main__":
    main()
