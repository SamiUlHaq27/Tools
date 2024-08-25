from ast import Constant, arg
import string
from time import sleep
import requests
from threading import Thread
import logging
import os
import random
from math import ceil

my_logger = logging.getLogger(__name__)
logging.basicConfig(filename='idm.log', encoding='utf-8', level=logging.DEBUG, filemode='w')

filename = 'GTA Liberty City.zip'
temp_path = 'E:/Code/Projects/Server/temp/'
download_path = 'E:/Code/Projects/Server/downloads/'
url  = 'http://127.0.0.1:5500/uploads/Grand%20Theft%20Auto%20-%20Liberty%20City%20Stories%20(USA)%20(En%2CFr%2CDe%2CEs%2CIt)%20(v3.00).7z'

chunk_size = 256 * 1024
max_segments = 4

class Status:
    
    ERROR = Constant(0)
    READY = Constant(1)
    PAUSED = Constant(2)
    CONNECTING = Constant(3)
    DOWNLOADING = Constant(4)
    COMPLETED = Constant(5)

class File:
    
    def __init__(self, url, file_name) -> None:
        self.url = url
        self.file_name = file_name
        self.resumeable = False
        self.parts = False
        self.status = Status.CONNECTING
        self.range_unit = None
        self.id = get_id(temp_path)
        
        os.mkdir(self.id)
        my_logger.info(f'url:{self.url} resume:{self.resumeable} parts:{self.parts} range:{self.range_unit}')
        
        self.res = requests.get(url, stream=True)
        if not self.res.status_code == 200:
            raise ConnectionError(f"status code = {self.res.status_code}")
        
        if self.res.headers.get('Accept-Ranges', False):
            self.parts = True
            self.range_unit = self.res.headers['Accept-Ranges']
        
        if self.res.headers.get('Connection', False) == 'keep-alive':
            self.resumeable = True
        self.total_size = int(self.res.headers['Content-Length'])
        
        self.status = Status.READY
    
    def start_downloading(self):
        self.segments = []
        
        if self.parts:
            self.create_segments(max_segments)
        else:
            my_logger.warning('Only one segement possible')
            self.segments.append(Segment(self.url, self.id))
            self.total_segements = 1
        
        for seg in self.segments:
            seg.start()
        
        self.th = Thread(target=check_completion, args=(self,))
        self.th.start()
    
    def pause_downloading(self):
        for seg in self.segments:
            seg.pause()
    
    def resume_downloading(self):
        for seg in self.segments:
            seg.resume()
        
    def create_segments(self, n):
        my_logger.info('Creating segments')
        seg_size = ceil(self.total_size/n)
        my_logger.info(f'Segment size: {seg_size}')
        start = 0
        end = seg_size-1
        for i in range(1, n):
            my_logger.info(f'Creted segment start:{start} end:{end}')
            self.segments.append(Segment(self.url, self.id, start, end, self.range_unit))
            start = end+1
            end += seg_size
        end = self.total_size
        self.segments.append(Segment(self.url, self.id, start, end, self.range_unit))
        my_logger.info(f'Created segment start:{start} end:{end}')
    
    def join_segments(self):
        files = [seg.id for seg in self.segments]
        with open(download_path+self.file_name,'wb') as f:
            for file in files:
                with open(f'{temp_path}{self.id}/{file}', 'rb') as seg:
                    f.write(seg.read())

class Segment:
    """
    Args:
    `url` the url of web resource 
    `start_point` the starting point of segement
    `ending_point` the ending point of segment
    `unit` the unit of range
    `id` the unique id for segment
    `on_progress` function for calling on progress
    """
    def __init__(self, url, file_id, start_point=0, ending_point=None, unit=None, on_progress=None):
        self.status = Status.CONNECTING
        self.res = requests.get(url, stream=True, headers={'range':f'{unit}={start_point}-{ending_point}'})
        self.file_id = file_id
        self.id = get_id(f'{temp_path}{file_id}/')
        self.range_unit = unit
        self.start_point = start_point
        self.ending_point = ending_point
        self.total_size = int(self.res.headers['Content-Length'])
        self.downloaded_size = 0
        self.status = Status.READY
    
    def start(self):
        self.status = Status.CONNECTING
        self.th = Thread(target=download_thread, args=(self,))
        self.th.start()
        my_logger.info(f'Segment: {self.id} started, start={self.start_point} end={self.ending_point}')

    def pause(self):
        self.status = Status.PAUSED
        my_logger.critical(f'Segment: {self.id} paused, down={self.downloaded_size} total={self.total_size}')

    def resume(self):
        self.status = Status.CONNECTING
        self.res = requests.get(url, stream=True, headers={'Range':f'{self.range_unit}={self.start_point+self.downloaded_size}-{self.ending_point}'})
        self.th = Thread(target=resume_thread, args=(self,))
        self.th.start()

def get_id(path):
    print(path)
    os.chdir(path)
    old_segments = os.listdir()
    while True:
        id = ''.join([random.choice(string.ascii_letters+string.digits) for i in range(5)])
        if id not in old_segments:
            return id

def download_thread(self:Segment):
    my_logger.info(f'Segment {self.id} started downloading...')
    self.status = Status.DOWNLOADING
    with open(temp_path+f'{self.file_id}/'+self.id, 'wb') as f:
        for chunk in self.res.iter_content(chunk_size):
            f.write(chunk)
            self.downloaded_size += chunk_size
            if self.status == Status.PAUSED:
                return 0
    self.status = Status.COMPLETED
    my_logger.info(f'Segment {self.id} completed')

def resume_thread(self:Segment):
    my_logger.info(f'Segment {self.id} is resuming...')
    self.status = Status.DOWNLOADING
    
    file_mode = 'ab'
    if self.res.status_code == 200:
        file_mode = 'wb'
        self.downloaded_size = 0
        my_logger.error('File cannot be resumed from location. Starting over from begining...')
        my_logger.error(f'Segment: {self.id} starting over')
    else:
        my_logger.info(f'Segment: {self.id} resumed, range={self.res.headers.get('Content-Range')}')
    
    with open(f'{temp_path}{self.file_id}/{self.id}', file_mode) as f:
        for chunk in self.res.iter_content(chunk_size):
            f.write(chunk)
            self.downloaded_size += chunk_size
            if self.status == Status.PAUSED:
                my_logger.critical(f'Segment {self.id} paused')
                return 0
    self.status = Status.COMPLETED
    my_logger.info(f'Segment {self.id} completed')

def check_completion(self:File):
    self.total_segments = len(self.segments)
    while True:
        self.completed_segments = 0
        for seg in self.segments:
            if seg.status == Status.COMPLETED:
                self.completed_segments += 1
        if self.total_segments == self.completed_segments:
            self.join_segments()
            break
        if self.status == Status.PAUSED:
            break

if __name__=='__main__':
    file = File(url, filename)
    file.start_downloading()
    sleep(2)
    file.pause_downloading()
    sleep(2)
    file.resume_downloading()
    