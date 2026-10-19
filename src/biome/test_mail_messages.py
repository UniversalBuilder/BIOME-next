import base64
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timezone
from mail_messages import extract_images, read_msg
from data_store import preview_import

class MailTests(unittest.TestCase):
    def attachment(self, raw, name="image.png"):
        return SimpleNamespace(attached_by_value=True,file_bytes=raw,file_name=name)
    def test_images_and_safe_names(self):
        raw=b"\x89PNG\r\n\x1a\nexample"
        result=extract_images([self.attachment(raw,"../../image.png"),self.attachment(b"document","manual.pdf")])
        self.assertEqual(result["files"][0]["name"],"image.png")
        self.assertEqual(base64.b64decode(result["files"][0]["content"]),raw)
        self.assertEqual(result["omitted"],1)
    def test_limits(self):
        result=extract_images([self.attachment(b"\x89PNG\r\n\x1a\n") for _ in range(101)])
        self.assertEqual(len(result["files"]),99)
        self.assertEqual(result["omitted"],2)

    def test_oversize_and_total_image_budget(self):
        image=self.attachment(b"\x89PNG\r\n\x1a\n"+b'x'*24)
        with patch('mail_messages.MAX_IMAGE_BYTES',31):
            self.assertEqual(extract_images([image])['omitted'],1)
        with patch('mail_messages.MAX_IMAGE_TOTAL_BYTES',50):
            result=extract_images([image,image])
            self.assertEqual(len(result['files']),1)
            self.assertEqual(result['omitted'],1)

    def test_large_message_and_illustration_survive_saving(self):
        from synthetic_fixture import create_fixture
        from data_store import add_entry
        raw=b'synthetic-message-' + b'x'*18_000_000
        image=b'\x89PNG\r\n\x1a\n'+b'x'*6_000_000
        message={'headers':[],'body':'Synthetic exchange','html':None,'date':None,
                 'images':extract_images([self.attachment(image),self.attachment(image,'second.png')])}
        with patch('mail_messages.read_msg',return_value=message):
            result=preview_import({'name':'synthetic.msg','content':base64.b64encode(raw).decode()})
        scratch=Path(__file__).parent/'test-tmp';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            root=Path(temp)/'project';create_fixture(root)
            import json,subprocess,sys,urllib.request
            command='from pathlib import Path;from server import serve;import sys;serve(Path(sys.argv[1]),0,Path(sys.argv[2]),state_dir=Path(sys.argv[3]))'
            state=Path(temp)/'state';state.mkdir()
            process=subprocess.Popen([sys.executable,'-u','-c',command,str(root.resolve()),str(state/'settings.json'),str(state)],cwd=Path(__file__).parent,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
            try:
                url=process.stdout.readline().strip().split()[-1]
                token=(state/'.local-session-token').read_text().strip()
                payload=json.dumps({'type':'exchange','date':'2026-10-19','time':'10:00','text':result['text'], 'attachments':[result['source'],*result['images']]}).encode()
                self.assertGreater(len(payload),35_000_000)
                request=urllib.request.Request(url+'/api/entries',data=payload,headers={'Content-Type':'application/json','X-Biome-Token':token})
                with urllib.request.urlopen(request,timeout=30) as response:entry=json.load(response)
            finally:
                process.terminate();process.wait(timeout=10);process.stdout.close()
            self.assertEqual(len(entry['attachments']),3)
            for record,expected in zip(entry['attachments'],[raw,image,image]):
                self.assertEqual((root/record['file']).read_bytes(),expected)
        with patch('data_store.MAX_MESSAGE_BYTES',10):
            with self.assertRaisesRegex(ValueError,'50 Mo'):
                preview_import({'name':'synthetic.msg','content':base64.b64encode(raw).decode()})
    def test_invalid_msg(self):
        with self.assertRaisesRegex(ValueError,"illisible"):
            read_msg(b"invalid")
    def test_preview_date_and_illustrations(self):
        message={"headers":[("Objet","A request")],"body":"Test [cid:illustration]","html":None,"date":datetime(2026,10,14,13,13,tzinfo=timezone.utc),"images":{"files":[{"name":"image.png","content":"abc"}],"omitted":0}}
        with patch("mail_messages.read_msg",return_value=message):
            result=preview_import({"name":"source.msg","content":base64.b64encode(b"source").decode()})
        self.assertEqual(result["time"],"15:13")
        self.assertEqual(len(result["images"]),1)
        self.assertNotIn("cid:",result["text"])
        self.assertEqual(base64.b64decode(result["source"]["content"]),b"source")

if __name__=="__main__":unittest.main()
