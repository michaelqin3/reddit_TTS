# Scrapes comments from reddit threads, reads them out using TTS and combines them into a narrated slideshow video
# Uses PRAW for reddit API, selenium to screenshot, and moviepy to create video

# TODO: 
#       add video clips while initially parsing through the comments instead of 2 iterations
#       sentence by sentence on vid instead of all at once
#           - break up into sentences, generate image frame of sentence and couple it with the TTS audio
#               - a ton more effort because we have to now have a frame per sentence and sync with TTS

from selenium.webdriver import Firefox, FirefoxOptions
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import praw
import time
import os
import pyttsx3
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from mutagen.wave import WAVE
import json

NUM_COMMENTS = 10
NUM_SUBMISSIONS = 2

with open('secretData.json') as f:
    SECRET_DATA = json.load(f)

opts = FirefoxOptions()
opts.add_argument("--headless")
opts.set_preference("dom.push.enabled", False)  # kill notification popup
drv = Firefox(executable_path=SECRET_DATA["gecko_exe_path"])
timeout = 10

commentIdToBody = {}
submissionIdToBody = {}
 
def authenticate():
    print('Authenticating...')

    reddit = reddit = praw.Reddit(
        client_id=SECRET_DATA["client_id"],
        client_secret=SECRET_DATA["client_secret"],
        user_agent="testscript by u/" + SECRET_DATA["username"],
    )

    print("Read only status: " + str(reddit.read_only))

    return reddit

def login():
    drv.get("https://www.reddit.com/login")
    user = drv.find_element(By.ID, "loginUsername")
    user.send_keys(SECRET_DATA["username"])
    pwd = drv.find_element(By.ID, "loginPassword")
    pwd.send_keys(SECRET_DATA["password"])
    btn = drv.find_element(By.CSS_SELECTOR, "button[type='submit']")
    btn.click()
    #cookie = drv.find_element(By.XPATH, '//button[text()="Accept all"]')
    #cookie.click()  # kill cookie agreement popup. Probably not needed now
    time.sleep(timeout)
 
 
def get_comments(reddit, target_sub, time_period):

    login()

    print('Obtaining comments...')
 
    with open("top_comments.txt", 'w') as f:
        f.write("Subreddt: " + target_sub + '\n\n')
        for submission in reddit.subreddit(target_sub).top(time_period, limit=NUM_SUBMISSIONS):
            cmts = "https://www.reddit.com" + submission.permalink
            drv.get(cmts)
            time.sleep(5)

            f.write("Thread:\n")
            f.write(submission.url + '\n')
            f.write(submission.title + '\n\n')

            submission.comment_sort = "top"
            submission.comment_limit = NUM_COMMENTS
            submission.comments.replace_more(limit=0)

            # create folder for thread
            try:
                os.makedirs('./' + submission.id)
            except FileExistsError:
                pass

            id = f"t3_{submission.id}"
            print("id= " + id)

            if save_screenshot(id,"./" + submission.id + "/" + submission.id + ".png"):
                submissionIdToBody[submission.id] = submission.title

            for comment in submission.comments:
                if comment.stickied:
                    continue
                f.write(comment.body + '\n\n\n')

                id = f"t1_{comment.id}"
                print("id= " + id)

                if save_screenshot(id, "./" + submission.id + "/" + comment.id + ".png"):
                    commentIdToBody[comment.id] = comment.body

def save_screenshot(id,filename):
    try:
        cmt = WebDriverWait(drv, timeout).until(
            lambda x: x.find_element(By.ID, id))
    except TimeoutException:
        print("Page load timed out...")
        return False
    else:
        cmt.screenshot(filename)
        return True

def add_clip(clips, text, path):
    engine = pyttsx3.init()
    clips = []

    # generate tts and save to file
    audio_name = path + ".wav"
    engine.save_to_file(text, audio_name)
    engine.runAndWait()
    audio_name = os.path.abspath(audio_name)

    # combine audio and image
    audio = WAVE(audio_name)
    audio_clip = AudioFileClip(audio_name)
    image_clip = ImageClip(path + ".png", duration=audio.info.length)
    image_clip = image_clip.set_audio(audio_clip)

    # append the ImageClip + tts
    clips.append(image_clip)
    return clips

def make_image_clips(os_entry):
    clips = []
    clips = add_clip(clips, submissionIdToBody[os_entry.name], "./" + os_entry.name + "/" + os_entry.name)
    
    for entry in os.scandir(os_entry.path):
        # get comment body and TTS and add audio to ImageClip
        if entry.name[-3:] != "png":
            continue

        print(entry.name)

        comment_id = entry.name.split(".")[0]

        if comment_id not in commentIdToBody:
            continue

        clips = add_clip(clips, commentIdToBody[comment_id],  "./" + os_entry.name + "/" + comment_id)

    # combine all clips into video
    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip.write_videofile("./" + os_entry.name + "/" + os_entry.name + ".mp4", fps=24)
 
def main():
    reddit = authenticate()
    get_comments(reddit, "askreddit", "week")
    for entry in os.scandir("./"):
        print(entry.path)
        print(entry.name)
        if entry.name in submissionIdToBody and entry.is_dir():
            make_image_clips(entry)
    drv.close()
    print("done")
 
if __name__ == '__main__':
    main()
