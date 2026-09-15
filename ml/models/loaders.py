import torch
from torchvision import models, transforms

def load_resnet50(device='cpu'):
    model = models.resnet50(pretrained=True)
    model.eval()
    model.to(device)
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])
    return model, preprocess


def load_yolov8(device='cpu'):
    try:
        from ultralytics import YOLO
    except Exception:
        raise RuntimeError("ultralytics package is required for YOLOv8")
    model = YOLO('yolov8n.pt')  # use small default weights; can be changed
    # ultralytics handles device placement via model.to()
    if device != 'cpu':
        model.to(device)
    return model
