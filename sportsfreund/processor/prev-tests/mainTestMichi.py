import os
import sys
import argparse
import cv2
from datetime import datetime
import requests


BASE_DIR = os.path.abspath(os.path.join(__file__, '../'))
sys.path.append(BASE_DIR)

from utils.utils import get_mediapipe_pose
from video.squats_processor import ProcessSquatsFrame
from thresholds import get_thresholds_squats

score = 0
def main(ex: str,video_path: str, live: bool):
    session_id = None
    exercise = "Squats"
    url = "http://localhost:3000/raspyfit/session"
    doingExercise = False
    data = {
        "start": datetime.now().isoformat()
    }

    response = requests.post(url, json=data)

    if response.ok:
        print("Session angelegt:", response.json())
        session_id = response.json()["sessionID"]
    else:
        print("Fehler:", response.status_code, response.text)

    pose = get_mediapipe_pose()

    if live :
        cap = cv2.VideoCapture(0)
    else:
        if not os.path.exists(video_path):
            print(f"[ERROR] File not found: {video_path}")
            return
        cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("[ERROR] Failed to open video file.")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS)) if not live else 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (width, height)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    output_path = 'output_recorded.mp4'
    if not live and os.path.exists(output_path):
        os.remove(output_path)

    out = None if live else cv2.VideoWriter(output_path, fourcc, fps, frame_size)

    frame_count = 0
    process_frame = None
    while cap.isOpened():

        if process_frame is not None:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            processed_frame, _ = process_frame.process(frame_rgb, pose)

        if not live and process_frame is not None and processed_frame is not None:
            out.write(processed_frame[..., ::-1])
        else:
            #1 ist ein Signal als Beispiel. In dem Fall für Squats
            if cv2.waitKey(1) & 0xFF == ord('1'):
                if doingExercise:
                    endExercise(process_frame, exercise, session_id)
                doingExercise = True
                exercise = 1
                thresholds = get_thresholds_squats()
                process_frame = ProcessSquatsFrame(thresholds=thresholds)
            elif cv2.waitKey(1) & 0xFF == ord('q'):
                if doingExercise:
                    endExercise(process_frame, exercise, session_id)
                endSession(session_id)



        frame_count += 1
        print(f"[INFO] Processed frame: {frame_count}", end='\r')

    cap.release()
    if not live:
        out.release()

        print(f"\n[INFO] Processing complete. Output saved to {output_path}")
    else:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Squat Analysis Tool")
    parser.add_argument('--ex', type=str, required=False, default="squat", help="Select exercise (squat,...)")
    parser.add_argument('--video', type=str, required=False, default="../samples/vali_squats.mp4", help="Select video path")
    parser.add_argument('--live', action='store_true', help="Run live using laptop camera")
    args = parser.parse_args()
    main(args.ex, args.video, args.live)


def endExercise(process_frame: ProcessSquatsFrame, exercise: int, session_id: int):
    state_tracker = getattr(process_frame, 'state_tracker', {})
    correct_reps = state_tracker.get('SQUAT_COUNT', 0)
    incorrect_reps = state_tracker.get('IMPROPER_SQUAT', 0)

    global score
    score = score + correct_reps

    payload = {
        "exerciseId": exercise,
        "sessionId": session_id,
        "repetitions": incorrect_reps,
        "score": correct_reps
    }

    try:
        response = requests.post("http://localhost:3000/raspyfit/sessions/exercise", json=payload)
        if response.status_code == 200:
            print("[INFO] Session successfully saved via backend!")
        else:
            print(f"[ERROR] Failed to save session. Status code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"[ERROR] Could not connect to backend: {e}")


def endSession(session_id):
    url = f"http://localhost:3000/raspyfit/session/{session_id}/endtime"
    data = {
        "end": datetime.now().date().isoformat(),
        "score": score
    }
    response = requests.patch(url, json=data)

    if response.ok:
        print("Session angelegt:", response.json())
    else:
        print("Fehler:", response.status_code, response.text)