"""Read Outlook messages locally; never render or execute their HTML."""
import base64
import io
import re
import sys
from pathlib import Path


MAX_MESSAGE_BYTES = 50_000_000
MAX_IMAGE_BYTES = 10_000_000
MAX_IMAGE_TOTAL_BYTES = 50_000_000
MAX_ENTRY_FILES = 100
MAX_ENTRY_BYTES = 100_000_000


def read_msg(raw, include_images=True):
    vendor=Path(__file__).with_name('vendor')
    if vendor.is_dir() and str(vendor) not in sys.path:
        sys.path.insert(0,str(vendor))
    try:
        from oxmsg import Message
    except ImportError:
        raise ValueError('Le lecteur Outlook MSG manque dans cette installation.')
    try:
        message=Message.load(io.BytesIO(raw))
        recipients=', '.join((item.name+' <'+item.email_address+'>') if item.email_address else item.name for item in message.recipients)
        headers=[('Objet',message.subject),('De',message.sender),('À',recipients)]
        date=message.sent_date
        if date: headers.append(('Date du message',date.isoformat()))
        return {'headers':headers,'body':message.body,'html':message.html_body,'date':date,
                'images':extract_images(message.attachments) if include_images else {'files':[], 'omitted':0}}
    except Exception:
        raise ValueError('Le message Outlook est illisible ou utilise un format non pris en charge.')


def extract_images(attachments):
    images=[];omitted=0;total=0
    for attachment in attachments:
        if not attachment.attached_by_value:
            omitted+=1;continue
        raw=attachment.file_bytes
        if not raw: continue
        extension=None
        if raw.startswith(b'\x89PNG\r\n\x1a\n'):extension='.png'
        elif raw.startswith(b'\xff\xd8\xff'):extension='.jpg'
        elif raw[:6] in [b'GIF87a',b'GIF89a']:extension='.gif'
        elif raw[:4]==b'RIFF' and raw[8:12]==b'WEBP':extension='.webp'
        if extension is None:
            omitted+=1;continue
        if len(raw)>MAX_IMAGE_BYTES or len(images)>=MAX_ENTRY_FILES-1 or total+len(raw)>MAX_IMAGE_TOTAL_BYTES:
            omitted+=1;continue
        name=re.split(r'[/\\]',attachment.file_name or '')[-1]
        name=re.sub(r'[\x00-\x1f:<>"|?*]','_',name).strip(' .')
        if not name:name='image-'+str(len(images)+1)+extension
        if Path(name).suffix.lower() not in ['.png','.jpg','.jpeg','.gif','.webp']:name+=extension
        images.append({'name':name,'content':base64.b64encode(raw).decode(),'role':'attachment',
                       'caption':'Illustration extraite du message Outlook'})
        total+=len(raw)
    return {'files':images,'omitted':omitted}
