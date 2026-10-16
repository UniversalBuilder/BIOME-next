"""Paginated activity report; vector charts and wrapped project summaries."""
import io, html
from collections import Counter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing, Rect, String

def create_pdf(report):
    buffer=io.BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42,title='BIOME - Bilan d’activité')
    styles=getSampleStyleSheet();styles['BodyText'].fontSize=10;styles['BodyText'].leading=14
    styles['Title'].textColor=colors.HexColor('#223d49')
    p=lambda text:Paragraph(html.escape(str(text)),styles['BodyText'])
    story=[Paragraph('BIOME - Bilan d’activité',styles['Title']),p('Période : '+report['start']+' au '+report['end']+' (dates incluses)'),Spacer(1,16),p(f"{report['total_minutes']//60} h {report['total_minutes']%60:02d} min renseignées | {len(report['projects'])} projets | {report['group_count']} groupes | {report['contact_count']} contacts"),Spacer(1,18)]
    def chart(title,counts,unit):
        section_start=len(story)
        values=sorted(counts.items(),key=lambda x:(-x[1],x[0]))
        story.append(Paragraph(title,styles['Heading2']))
        if not values: story.append(p('Aucune donnée renseignée.'));return
        maximum=max([v for _,v in values]+[1])
        for label,value in values:
            drawing=Drawing(500,22)
            drawing.add(Rect(0,4,400*value/maximum,12,fillColor=colors.HexColor('#46858a'),strokeColor=None))
            drawing.add(String(410,6,str(round(value,2))+' '+unit,fontSize=9))
            story.append(KeepTogether([p(label),drawing,Spacer(1,6)]))

    groups=Counter()
    for row in report['projects']:
        if row['minutes'] is not None: groups[row['group'] or 'Non renseigné']+=row['minutes']/60
    chart('Temps humain par groupe',groups,'h')
    story.extend([Spacer(1,12),p('Les graphiques scientifiques comptent les projets, pas les heures. Un même projet peut figurer dans plusieurs catégories. Les catégories et statuts sont les valeurs actuelles du projet.')])
    for key,title in [('activity_type','Interventions principales'),('software','Logiciels utilisés'),('modalities','Modalités d’imagerie'),('topics','Thématiques d’analyse')]:
        story.append(PageBreak() if key=='topics' else Spacer(1,18))
        names={'consulting':'Conseil / consulting','training':'Formation','development':'Développement de script / workflow','analysis':'Analyse de données'}
        counts=Counter()
        for row in report['projects']:
            values=row[key] if isinstance(row[key],list) else [row[key]]
            counts.update(set(names.get(v,v) for v in values if v))
        chart(title,counts,'projet(s)')
        missing=sum(not row[key] for row in report['projects'])
        story.extend([Spacer(1,10),p(str(missing)+' projet(s) sans catégorie renseignée.')])
    story.extend([PageBreak(),Paragraph('Détail des projets',styles['Heading1'])])
    statuses={'Intake':'À cadrer','Active':'En cours','Review':'En validation','Completed':'Terminé','OnHold':'En pause'}
    for row in report['projects']:
        story.append(Paragraph(html.escape(row['title']),styles['Heading2']))
        minutes=row['minutes'];duration='Non renseigné' if minutes is None else f'{minutes//60} h {minutes%60:02d} min'
        rows=[['Groupe',row['group'] or 'Non renseigné'],['Contact',row['contact'] or 'Non renseigné'],['Statut actuel',statuses.get(row['status'],row['status'])],['Temps / séances',duration+' / '+str(row['session_count'])],['Logiciels',', '.join(row['software']) or 'Non renseigné'],['Modalités',', '.join(row['modalities']) or 'Non renseigné'],['Thématiques',', '.join(row['topics']) or 'Non renseigné']]
        table=Table([[p(a),p(b)] for a,b in rows],colWidths=[110,401],hAlign='LEFT')
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#dddddd')),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.extend([table,Spacer(1,16)])
    story.extend([Paragraph('Lecture du bilan',styles['Heading2']),p('Temps humain saisi à la date des séances. Un temps absent ne signifie pas zéro travail. '+str(report['entries_without_time'])+' entrées ne sont reliées à aucune saisie de temps. Aucune répartition du temps entre logiciels n’est supposée.')])
    if report['warnings']: story.append(p('Dossiers non comptabilisés : '+'; '.join(report['warnings'])))
    def footer(canvas,document):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.grey)
        canvas.drawString(42,24,'BIOME | '+report['start']+' - '+report['end']);canvas.drawRightString(A4[0]-42,24,str(document.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()

