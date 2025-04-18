import os
import sys
import argparse
import cv2

BASE_DIR = os.path.abspath(os.path.join(__file__, '../../'))
sys.path.append(BASE_DIR)

from utils.utils import get_mediapipe_pose
from video.squats_processor import ProcessSquatsFrame
from thresholds import get_thresholds_squats


def main(ex: str, video_path: str):
    if not os.path.exists(video_path):
        print(f"[ERROR] File not found: {video_path}")
        return
    thresholds = get_thresholds_squats()

    match ex.lower():
        case "squats":
            process_frame = ProcessSquatsFrame(thresholds=thresholds)

    pose = get_mediapipe_pose()

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("[ERROR] Failed to open video file.")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (width, height)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    output_path = 'output_recorded.mp4'
    if os.path.exists(output_path):
        os.remove(output_path)

    out = cv2.VideoWriter(output_path, fourcc, fps, frame_size)

    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        processed_frame, _ = process_frame.process(frame_rgb, pose)
        out.write(processed_frame[..., ::-1]) 

        frame_count += 1
        print(f"[INFO] Processed frame: {frame_count}", end='\r')

    cap.release()
    out.release()

    print(f"\n[INFO] Processing complete. Output saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Squat Analysis Tool")
    parser.add_argument('--ex', type=str, required=False,default="squats", help="Select exercise (squats,...)")
    parser.add_argument('--video', type=str, required=False,default="../samples/squats.mp4", help="Select video path")
    args = parser.parse_args()
    main(args.ex, args.video)
