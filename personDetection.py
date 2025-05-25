import cv2
import torch
import numpy as np

# Load YOLOv5 model from PyTorch Hub
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
model.conf = 0.5  # confidence threshold

# Open webcam or video file
cap = cv2.VideoCapture("data/szymek_drone2.mp4")  # Replace 0 with 'your_video.mp4' if needed

# Get video properties
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
fps = cap.get(cv2.CAP_PROP_FPS) or 30  # fallback to 30 if FPS not available

# Define video writer
out = cv2.VideoWriter(
    'output.avi',
    cv2.VideoWriter_fourcc(*'XVID'),
    fps,
    (frame_width, frame_height)
)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convert frame (BGR to RGB)
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Perform inference
    results = model(img)

    # Parse predictions
    detections = results.xyxy[0].cpu().numpy()

    for *box, conf, cls in detections:
        if int(cls) == 0:  # class 0 = 'person'
            x1, y1, x2, y2 = map(int, box)
            label = f"Person (dead) {conf:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Write the frame with boxes to the output file
    out.write(frame)

    # Show live
    cv2.imshow('YOLOv5 Person Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
out.release()
cv2.destroyAllWindows()
