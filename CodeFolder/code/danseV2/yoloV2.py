#yolo pose predict model=yolov8n-pose.pt source=0 show=true
#--------------------V4--------------------#
import cv2
import numpy as np
from ultralytics import YOLO
import threading
import UdpComms as U

class PoseAnalyzer:
    def __init__(self):
        # Initialisation du modèle YOLO et du signal de démarrage
        self.model = None
        self.startSignal = threading.Event()
        self.initializeYolo()

        # Configuration de la communication UDP
        self.udpCommunicator = U.UdpComms(udpIP="127.0.0.1", portTX=8000, portRX=8001, enableRX=True, suppressWarnings=True)

        # Configuration de la caméra
        self.cap = cv2.VideoCapture(0)

    def initializeYolo(self):
        # Initialiser YOLO dans un thread séparé
        yoloInitThread = threading.Thread(target=self.initializeYoloThread)
        yoloInitThread.start()

        # Attendre le signal d'initialisation
        yoloInitThread.join()

    def initializeYoloThread(self):
        # Initialiser le modèle YOLO
        self.model = YOLO("yolov8n-pose.pt")
        self.startSignal.set()

    # Fonction utilitaire pour calculer la distance entre deux points
    @staticmethod #fonctions utilitaires qui effectuent des calculs géométriques et n'ont pas besoin d'accéder aux attributs d'instance spécifiques.
    def calculateDistance(a, b):
        return np.sqrt(((a[0] - b[0]) ** 2) + ((a[1] - b[1]) ** 2))

    # Fonction utilitaire pour calculer l'angle entre trois points
    @staticmethod #fonctions utilitaires qui effectuent des calculs géométriques et n'ont pas besoin d'accéder aux attributs d'instance spécifiques.
    def calculateAngle(a, b, c):
        v1 = np.array([a[0] - b[0], a[1] - b[1]])
        v2 = np.array([c[0] - b[0], c[1] - b[1]])
        return np.degrees(np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))))

    # Fonction pour déterminer le côté (gauche, droite, centre) en fonction des positions des épaules et des hanches
    @staticmethod #fonctions utilitaires qui effectuent des calculs géométriques et n'ont pas besoin d'accéder aux attributs d'instance spécifiques.
    def getSide(positions):
        leftSide = PoseAnalyzer.calculateDistance(positions["left_shoulder"], positions["left_hip"])
        rightSide = PoseAnalyzer.calculateDistance(positions["right_shoulder"], positions["right_hip"])

        return "gauche" if leftSide > rightSide else "droite" if leftSide < rightSide else "centre"

    # Fonction pour déterminer l'inclinaison de la tête (gauche, droite, centre) en fonction des positions des oreilles et des épaules
    @staticmethod #fonctions utilitaires qui effectuent des calculs géométriques et n'ont pas besoin d'accéder aux attributs d'instance spécifiques.
    def getHeadInclination(positions):
        leftSide = PoseAnalyzer.calculateDistance(positions["left_ear"], positions["left_shoulder"])
        rightSide = PoseAnalyzer.calculateDistance(positions["right_ear"], positions["right_shoulder"])

        return "gauche" if leftSide > rightSide else "droite" if leftSide < rightSide else "centre"

    # Fonction pour traiter chaque frame de la caméra
    def processFrame(self, frame):
        # Effectuer les prédictions YOLO
        results = self.model(frame)
        f = results[0].plot()
        keypoints = results[0].keypoints.xy.tolist()
        peoples = list()

        for person in keypoints:
            if not person:
                continue

            positions = {
                "nose": person[0],
                "left_eye": person[1],
                "right_eye": person[2],
                "left_ear": person[3],
                "right_ear": person[4],
                "left_shoulder": person[5],
                "right_shoulder": person[6],
                "left_elbow": person[7],
                "right_elbow": person[8],
                "left_wrist": person[9],
                "right_wrist": person[10],
                "left_hip": person[11],
                "right_hip": person[12],
                "left_knee": person[13],
                "right_knee": person[14],
                "left_ankle": person[15],
                "right_ankle": person[16]
            }
            peoples.append(positions)
            wristDistance = PoseAnalyzer.calculateDistance(positions["left_wrist"], positions["right_wrist"])
            leftArmAngle = round(PoseAnalyzer.calculateAngle(positions["left_shoulder"], positions["left_elbow"], positions["left_wrist"]), 2)
            rightArmAngle = round(PoseAnalyzer.calculateAngle(positions["right_shoulder"], positions["right_elbow"], positions["right_wrist"]), 2)
            leftShoulderAngle = round(PoseAnalyzer.calculateAngle(positions["left_hip"], positions["left_shoulder"], positions["left_elbow"]), 2)
            rightShoulderAngle = round(PoseAnalyzer.calculateAngle(positions["right_hip"], positions["right_shoulder"], positions["right_elbow"]), 2)
            headInclination = PoseAnalyzer.getHeadInclination(positions)

            # Dessiner les angles sur l'image
            self.drawAngles(f, positions, leftArmAngle, rightArmAngle, leftShoulderAngle, rightShoulderAngle, headInclination)

            # Envoyer les données à Unity
            self.udpCommunicator.SendData("distance poignet : " + str(wristDistance))
            self.udpCommunicator.SendData("points du corp : " + str(peoples))

        return f

    # Fonction pour dessiner les angles sur l'image
    @staticmethod #fonctions utilitaires qui effectuent des calculs géométriques et n'ont pas besoin d'accéder aux attributs d'instance spécifiques.
    def drawAngles(frame, positions, leftArmAngle, rightArmAngle, leftShoulderAngle, rightShoulderAngle, headInclination):
        cv2.putText(frame, str(leftArmAngle), (int(positions["left_elbow"][0]), int(positions["left_elbow"][1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, str(rightArmAngle), (int(positions["right_elbow"][0]), int(positions["right_elbow"][1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, str(leftShoulderAngle), (int(positions["left_shoulder"][0]), int(positions["left_shoulder"][1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, str(rightShoulderAngle), (int(positions["right_shoulder"][0]), int(positions["right_shoulder"][1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, str(headInclination), (int(positions["nose"][0]), int(positions["nose"][1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Fonction pour exécuter l'analyseur de pose
    def run(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            processedFrame = self.processFrame(frame)

            # Afficher l'image
            cv2.imshow('Image originale', processedFrame)

            if cv2.waitKey(1) == ord('q'):
                break

        # Fermer les sockets et libérer la caméra
        self.udpCommunicator.Close()
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Instancier et exécuter l'analyseur de pose
    poseAnalyzer = PoseAnalyzer()
    poseAnalyzer.run()

#--------------------V3--------------------#
# import cv2
# import numpy as np
# from ultralytics import YOLO
# import threading

# import UdpComms as U

# model = None
# start_signal = threading.Event()

# # Initialize YOLO
# def initialize_yolo():
#     global model
#     model = YOLO("yolov8n-pose.pt")
#     start_signal.set()

# # Start the initialization thread
# yolo_init_thread = threading.Thread(target=initialize_yolo)
# yolo_init_thread.start()

# # Wait for the initialization signal
# while not start_signal.is_set():
#     pass

# # UDP communication setup
# udp_communicator = U.UdpComms(udpIP="127.0.0.1", portTX=8000, portRX=8001, enableRX=True, suppressWarnings=True)

# # Camera setup
# cap = cv2.VideoCapture(0)

# def distance(a, b):
#     return np.sqrt(((a[0] - b[0]) ** 2) + ((a[1] - b[1]) ** 2))
    
# def angle(a, b, c):
#     v1 = np.array([a[0] - b[0], a[1] - b[1]])
#     v2 = np.array([c[0] - b[0], c[1] - b[1]])
#     return np.degrees(np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))))

# def get_side(positions):
#     left_side = distance(positions["left_shoulder"], positions["left_hip"])
#     right_side = distance(positions["right_shoulder"], positions["right_hip"])

#     if left_side > right_side:
#         return "gauche"
#     elif left_side < right_side:
#         return "droite"
#     else:
#         return "centre"

# def get_head_inclination(positions):
#     left_side = distance(positions["left_ear"], positions["left_shoulder"])
#     right_side = distance(positions["right_ear"], positions["right_shoulder"])

#     if left_side > right_side:
#         return "gauche"
#     elif left_side < right_side:
#         return "droite"
#     else:
#         return "centre"

# while True:
#     ret, frame = cap.read()
#     if not ret:
#         break

#     # Perform YOLO predictions
#     results = model(frame)
#     f = results[0].plot()
#     keypoints = results[0].keypoints.xy.tolist()
#     peoples = list()

#     for person in keypoints:
#         if len(person) == 0:
#             continue

#         positions = {
#             "nose":              person[0],
#             "left_eye":          person[1],
#             "right_eye":         person[2],
#             "left_ear":          person[3],
#             "right_ear":         person[4],
#             "left_shoulder":     person[5],
#             "right_shoulder":    person[6],
#             "left_elbow":        person[7],
#             "right_elbow":       person[8],
#             "left_wrist":        person[9],
#             "right_wrist":       person[10],
#             "left_hip":          person[11],
#             "right_hip":         person[12],
#             "left_knee":         person[13],
#             "right_knee":        person[14],
#             "left_ankle":        person[15],
#             "right_ankle":       person[16]
#         }
#         peoples.append(positions)
#         wrist_distance = distance(positions["left_wrist"], positions["right_wrist"])
#         left_arm_angle = round(angle(positions["left_shoulder"], positions["left_elbow"], positions["left_wrist"]), 2)
#         right_arm_angle = round(angle(positions["right_shoulder"], positions["right_elbow"], positions["right_wrist"]), 2)
#         left_shoulder_angle = round(angle(positions["left_hip"], positions["left_shoulder"], positions["left_elbow"]), 2)
#         right_shoulder_angle = round(angle(positions["right_hip"], positions["right_shoulder"], positions["right_elbow"]), 2)
#         head_inclination = get_head_inclination(positions)

#         # draw angle on image
#         cv2.putText(f, str(left_arm_angle), (int(positions["left_elbow"][0]), int(positions["left_elbow"][1])),
#                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#         cv2.putText(f, str(right_arm_angle), (int(positions["right_elbow"][0]), int(positions["right_elbow"][1])),
#                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#         cv2.putText(f, str(left_shoulder_angle), (int(positions["left_shoulder"][0]), int(positions["left_shoulder"][1])),
#                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#         cv2.putText(f, str(right_shoulder_angle), (int(positions["right_shoulder"][0]), int(positions["right_shoulder"][1])),
#                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#         cv2.putText(f, str(head_inclination), (int(positions["nose"][0]), int(positions["nose"][1])),
#                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

#         # Send data to Unity
#         udp_communicator.SendData("distance poignet : " + str(wrist_distance))
#         udp_communicator.SendData("points du corp : " + str(peoples))

        

#     # Display the image
#     cv2.imshow('Original Image', f)

#     if cv2.waitKey(1) == ord('q'):
#         break

# # Close the sockets and release the camera
# udp_communicator.Close()
# cap.release()
# cv2.destroyAllWindows()


#--------------------V2--------------------#

# from ultralytics import YOLO
# import cv2
# import numpy as np

# model = YOLO("yolov8n-pose.pt")

# # Charger l'image d'entrée
# cap = cv2.VideoCapture(0)

# def distance(a, b):
#     return np.sqrt(((a[0] - b[0]) ** 2) + ((a[1] - b[1]) ** 2))

# def angle(a, b, c):
#     v1 = np.array([a[0] - b[0], a[1] - b[1]])
#     v2 = np.array([c[0] - b[0], c[1] - b[1]])
#     return np.degrees(np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))))

# def get_side(positions):
#     left_side = distance(positions["left_shoulder"], positions["left_hip"])
#     right_side = distance(positions["right_shoulder"], positions["right_hip"])
    
#     if left_side > right_side:
#         return "gauche"
#     elif left_side < right_side:
#         return "droite"
#     else:
#         return "centre"
    
# def get_head_inclination(positions):
#     left_side = distance(positions["left_ear"], positions["left_shoulder"])
#     right_side = distance(positions["right_ear"], positions["right_shoulder"])
    
#     if left_side > right_side:
#         return "gauche"
#     elif left_side < right_side:
#         return "droite"
#     else:
#         return "centre"
    


# while True:
#     ret, frame = cap.read()
#     if not ret:
#         break
    
#     # Prédire les poses
#     results = model(frame)
#     f = results[0].plot()
#     keypoints = results[0].keypoints.xy.tolist()
#     keypoints_normalized = results[0].keypoints.xyn.tolist()
#     peoples = list()

#     for person in keypoints:
#         if len(person) == 0:
#             continue
        
#         positions = {
#             "nose":              person[0],
#             "left_eye":          person[1],
#             "right_eye":         person[2],
#             "left_ear":          person[3],
#             "right_ear":         person[4],
#             "left_shoulder":     person[5],
#             "right_shoulder":    person[6],
#             "left_elbow":        person[7],
#             "right_elbow":       person[8],
#             "left_wrist":        person[9],
#             "right_wrist":       person[10],
#             "left_hip":          person[11],
#             "right_hip":         person[12],
#             "left_knee":         person[13],
#             "right_knee":        person[14],
#             "left_ankle":        person[15],
#             "right_ankle":       person[16]
#         }
#         peoples.append(positions)
#         left_arm_angle = round(angle(positions["left_shoulder"], positions["left_elbow"], positions["left_wrist"]), 2)
#         right_arm_angle = round(angle(positions["right_shoulder"], positions["right_elbow"], positions["right_wrist"]), 2)
#         left_shoulder_angle = round(angle(positions["left_hip"], positions["left_shoulder"], positions["left_elbow"]), 2)
#         right_shoulder_angle = round(angle(positions["right_hip"], positions["right_shoulder"], positions["right_elbow"]), 2)
#         head_inclination = get_head_inclination(positions)
        
#         #draw angle on image
#         cv2.putText(f, str(left_arm_angle), (int(positions["left_elbow"][0]), int(positions["left_elbow"][1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#         cv2.putText(f, str(right_arm_angle), (int(positions["right_elbow"][0]), int(positions["right_elbow"][1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#         cv2.putText(f, str(left_shoulder_angle), (int(positions["left_shoulder"][0]), int(positions["left_shoulder"][1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#         cv2.putText(f, str(right_shoulder_angle), (int(positions["right_shoulder"][0]), int(positions["right_shoulder"][1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
#         cv2.putText(f, str(head_inclination), (int(positions["nose"][0]), int(positions["nose"][1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
    
        
#     # Afficher l'image
#     cv2.imshow('Image d\'origine', f)

#     if cv2.waitKey(1) == ord('q'):
#         break
    
# cap.release()
# cv2.destroyAllWindows()



#--------------------V1--------------------#
# from ultralytics import YOLO
# import cv2

# # Créez une instance YOLOv8 avec l'option stream=True
# yolo = YOLO(model='yolov8m-pose.pt')

# # Capturez la vidéo de votre webcam
# cap = cv2.VideoCapture(0)

# for results in yolo.predict(source="0", show=True, conf=0.4):  # Utilisez une boucle pour obtenir les résultats en continu
#     frame = results[0]  # Obtenez l'image avec les détections

#     # Affichez le cadre avec les détections
#     cv2.imshow('YOLOv8 Pose Detection', frame)

#     # Pour quitter, appuyez sur 'q'
#     if cv2.waitKey(1) == ord('q'):
#         break

# cap.release()
# cv2.destroyAllWindows()

