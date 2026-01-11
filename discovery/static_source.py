"""
Static source with known tech companies hiring in various locations.
Used as a fallback and starting point for discovery.
"""

from typing import List, Generator, Dict
from models import Company
from utils import get_logger
from .base_source import BaseSource


class StaticCompanySource(BaseSource):
    """
    Static database of known tech companies by location.
    Useful as a starting point and fallback.
    """
    
    # Database of known tech companies with careers pages
    COMPANIES_DB: Dict[str, List[Dict]] = {
        'berlin': [
            {'name': 'Zalando', 'website': 'https://jobs.zalando.com', 'careers': 'https://jobs.zalando.com/en/jobs'},
            {'name': 'N26', 'website': 'https://n26.com', 'careers': 'https://n26.com/en/careers'},
            {'name': 'SoundCloud', 'website': 'https://soundcloud.com', 'careers': 'https://soundcloud.com/jobs'},
            {'name': 'HelloFresh', 'website': 'https://www.hellofresh.com', 'careers': 'https://www.hellofresh.com/careers'},
            {'name': 'Delivery Hero', 'website': 'https://www.deliveryhero.com', 'careers': 'https://careers.deliveryhero.com'},
            {'name': 'GetYourGuide', 'website': 'https://www.getyourguide.com', 'careers': 'https://careers.getyourguide.com'},
            {'name': 'Contentful', 'website': 'https://www.contentful.com', 'careers': 'https://www.contentful.com/careers'},
            {'name': 'Adjust', 'website': 'https://www.adjust.com', 'careers': 'https://www.adjust.com/company/careers'},
            {'name': 'Trade Republic', 'website': 'https://traderepublic.com', 'careers': 'https://traderepublic.com/careers'},
            {'name': 'Personio', 'website': 'https://www.personio.com', 'careers': 'https://www.personio.com/about-personio/careers'},
            {'name': 'Pitch', 'website': 'https://pitch.com', 'careers': 'https://pitch.com/about'},
            {'name': 'Gorillas', 'website': 'https://gorillas.io', 'careers': 'https://gorillas.io/en/careers'},
            {'name': 'Wolt', 'website': 'https://wolt.com', 'careers': 'https://careers.wolt.com'},
            {'name': 'Omio', 'website': 'https://www.omio.com', 'careers': 'https://www.omio.com/careers'},
            {'name': 'Taxfix', 'website': 'https://taxfix.de', 'careers': 'https://taxfix.de/en/careers'},
            {'name': 'Blinkist', 'website': 'https://www.blinkist.com', 'careers': 'https://www.blinkist.com/careers'},
            {'name': 'Ecosia', 'website': 'https://www.ecosia.org', 'careers': 'https://www.ecosia.org/jobs'},
            {'name': 'Babbel', 'website': 'https://www.babbel.com', 'careers': 'https://www.babbel.com/careers'},
            {'name': 'Klarna', 'website': 'https://www.klarna.com', 'careers': 'https://www.klarna.com/careers'},
            {'name': 'Tier Mobility', 'website': 'https://www.tier.app', 'careers': 'https://www.tier.app/careers'},
            {'name': 'Moonfare', 'website': 'https://www.moonfare.com', 'careers': 'https://www.moonfare.com/careers'},
            {'name': 'Clark', 'website': 'https://www.clark.de', 'careers': 'https://www.clark.de/de/jobs'},
            {'name': 'Raisin', 'website': 'https://www.raisin.com', 'careers': 'https://www.raisin.com/careers'},
            {'name': 'Home24', 'website': 'https://www.home24.de', 'careers': 'https://www.home24.de/karriere'},
            {'name': 'Smava', 'website': 'https://www.smava.de', 'careers': 'https://www.smava.de/karriere'},
        ],
        'munich': [
            {'name': 'Celonis', 'website': 'https://www.celonis.com', 'careers': 'https://www.celonis.com/careers'},
            {'name': 'FlixBus', 'website': 'https://www.flixbus.com', 'careers': 'https://www.flixbus.com/company/jobs'},
            {'name': 'Lilium', 'website': 'https://lilium.com', 'careers': 'https://lilium.com/careers'},
            {'name': 'ProSiebenSat.1', 'website': 'https://www.prosiebensat1.com', 'careers': 'https://www.prosiebensat1.com/karriere'},
            {'name': 'Siemens', 'website': 'https://www.siemens.com', 'careers': 'https://www.siemens.com/global/en/company/jobs.html'},
            {'name': 'BMW', 'website': 'https://www.bmw.com', 'careers': 'https://www.bmwgroup.jobs'},
            {'name': 'Allianz', 'website': 'https://www.allianz.com', 'careers': 'https://careers.allianz.com'},
            {'name': 'IDnow', 'website': 'https://www.idnow.io', 'careers': 'https://www.idnow.io/career'},
            {'name': 'Sono Motors', 'website': 'https://sonomotors.com', 'careers': 'https://sonomotors.com/en/career'},
            {'name': 'Stylight', 'website': 'https://www.stylight.com', 'careers': 'https://about.stylight.com/jobs'},
        ],
        'london': [
            {'name': 'Revolut', 'website': 'https://www.revolut.com', 'careers': 'https://www.revolut.com/careers'},
            {'name': 'Monzo', 'website': 'https://monzo.com', 'careers': 'https://monzo.com/careers'},
            {'name': 'Deliveroo', 'website': 'https://deliveroo.co.uk', 'careers': 'https://careers.deliveroo.co.uk'},
            {'name': 'Checkout.com', 'website': 'https://www.checkout.com', 'careers': 'https://www.checkout.com/careers'},
            {'name': 'GoCardless', 'website': 'https://gocardless.com', 'careers': 'https://gocardless.com/about/careers'},
            {'name': 'Improbable', 'website': 'https://www.improbable.io', 'careers': 'https://www.improbable.io/careers'},
            {'name': 'TransferWise', 'website': 'https://wise.com', 'careers': 'https://wise.com/careers'},
            {'name': 'Starling Bank', 'website': 'https://www.starlingbank.com', 'careers': 'https://www.starlingbank.com/careers'},
            {'name': 'Citymapper', 'website': 'https://citymapper.com', 'careers': 'https://citymapper.com/jobs'},
            {'name': 'Bulb', 'website': 'https://bulb.co.uk', 'careers': 'https://bulb.co.uk/careers'},
        ],
        'amsterdam': [
            {'name': 'Booking.com', 'website': 'https://www.booking.com', 'careers': 'https://jobs.booking.com'},
            {'name': 'Adyen', 'website': 'https://www.adyen.com', 'careers': 'https://careers.adyen.com'},
            {'name': 'Elastic', 'website': 'https://www.elastic.co', 'careers': 'https://www.elastic.co/about/careers'},
            {'name': 'Takeaway', 'website': 'https://www.takeaway.com', 'careers': 'https://www.takeaway.com/jobs'},
            {'name': 'Messagebird', 'website': 'https://www.messagebird.com', 'careers': 'https://www.messagebird.com/careers'},
        ],
        'paris': [
            {'name': 'Doctolib', 'website': 'https://www.doctolib.fr', 'careers': 'https://careers.doctolib.com'},
            {'name': 'BlaBlaCar', 'website': 'https://www.blablacar.com', 'careers': 'https://blog.blablacar.com/careers'},
            {'name': 'Datadog', 'website': 'https://www.datadoghq.com', 'careers': 'https://www.datadoghq.com/careers'},
            {'name': 'Criteo', 'website': 'https://www.criteo.com', 'careers': 'https://careers.criteo.com'},
            {'name': 'Contentsquare', 'website': 'https://contentsquare.com', 'careers': 'https://contentsquare.com/careers'},
        ],
        'default': [
            {'name': 'GitLab', 'website': 'https://about.gitlab.com', 'careers': 'https://about.gitlab.com/jobs'},
            {'name': 'Automattic', 'website': 'https://automattic.com', 'careers': 'https://automattic.com/work-with-us'},
            {'name': 'Zapier', 'website': 'https://zapier.com', 'careers': 'https://zapier.com/jobs'},
            {'name': 'Buffer', 'website': 'https://buffer.com', 'careers': 'https://buffer.com/journey'},
            {'name': 'Doist', 'website': 'https://doist.com', 'careers': 'https://doist.com/careers'},
            {'name': 'InVision', 'website': 'https://www.invisionapp.com', 'careers': 'https://www.invisionapp.com/about#jobs'},
            {'name': 'Basecamp', 'website': 'https://basecamp.com', 'careers': 'https://basecamp.com/about/jobs'},
            {'name': 'Toptal', 'website': 'https://www.toptal.com', 'careers': 'https://www.toptal.com/careers'},
            {'name': 'Remote', 'website': 'https://remote.com', 'careers': 'https://remote.com/careers'},
            {'name': 'Deel', 'website': 'https://www.deel.com', 'careers': 'https://www.deel.com/careers'},
        ],
        # India - Kerala and major tech hubs (MASSIVELY EXPANDED)
        'kerala': [
            # Major IT Companies in Kerala
            {'name': 'UST Global', 'website': 'https://www.ust.com', 'careers': 'https://www.ust.com/en/careers'},
            {'name': 'IBS Software', 'website': 'https://www.ibsplc.com', 'careers': 'https://www.ibsplc.com/careers'},
            {'name': 'Suntec Business Solutions', 'website': 'https://www.suntecgroup.com', 'careers': 'https://www.suntecgroup.com/careers'},
            {'name': 'QBurst', 'website': 'https://www.qburst.com', 'careers': 'https://www.qburst.com/en/careers'},
            {'name': 'KeyValue Software Systems', 'website': 'https://www.keyvalue.systems', 'careers': 'https://www.keyvalue.systems/careers'},
            {'name': 'Fingent', 'website': 'https://www.fingent.com', 'careers': 'https://www.fingent.com/careers'},
            {'name': 'Experion Technologies', 'website': 'https://experionglobal.com', 'careers': 'https://experionglobal.com/career'},
            {'name': 'Techversant Infotech', 'website': 'https://techversantinfotech.com', 'careers': 'https://techversantinfotech.com/careers'},
            {'name': 'NeST Digital', 'website': 'https://nestdigital.com', 'careers': 'https://nestdigital.com/careers'},
            {'name': 'Speridian Technologies', 'website': 'https://www.speridian.com', 'careers': 'https://www.speridian.com/careers'},
            # Kochi Infopark Companies
            {'name': 'TCS Kochi', 'website': 'https://www.tcs.com', 'careers': 'https://www.tcs.com/careers'},
            {'name': 'Infosys Trivandrum', 'website': 'https://www.infosys.com', 'careers': 'https://www.infosys.com/careers'},
            {'name': 'Wipro Kerala', 'website': 'https://www.wipro.com', 'careers': 'https://careers.wipro.com'},
            {'name': 'Tech Mahindra Kochi', 'website': 'https://www.techmahindra.com', 'careers': 'https://careers.techmahindra.com'},
            {'name': 'Envestnet Trivandrum', 'website': 'https://www.envestnet.com', 'careers': 'https://www.envestnet.com/careers'},
            {'name': 'Cognizant Kochi', 'website': 'https://www.cognizant.com', 'careers': 'https://careers.cognizant.com'},
            {'name': 'HCL Technologies Kochi', 'website': 'https://www.hcltech.com', 'careers': 'https://www.hcltech.com/careers'},
            {'name': 'Capgemini Trivandrum', 'website': 'https://www.capgemini.com', 'careers': 'https://www.capgemini.com/careers'},
            # Technopark Companies (Trivandrum)
            {'name': 'Ernst & Young Kerala', 'website': 'https://www.ey.com', 'careers': 'https://www.ey.com/en_in/careers'},
            {'name': 'Oracle India Trivandrum', 'website': 'https://www.oracle.com', 'careers': 'https://www.oracle.com/in/careers'},
            {'name': 'NTT DATA Kerala', 'website': 'https://www.nttdata.com', 'careers': 'https://www.nttdata.com/global/en/careers'},
            {'name': 'Allianz Technology Kerala', 'website': 'https://www.allianz.com', 'careers': 'https://careers.allianz.com'},
            {'name': 'Toonz Media Group', 'website': 'https://www.toonzgroup.com', 'careers': 'https://www.toonzgroup.com/careers'},
            # Mid-size IT Companies
            {'name': 'Triassic Solutions', 'website': 'https://www.triassicsolutions.com', 'careers': 'https://www.triassicsolutions.com/careers'},
            {'name': 'Deltasymbol IT Solutions', 'website': 'https://www.deltasymbol.in', 'careers': 'https://www.deltasymbol.in/careers'},
            {'name': 'Oureasoft', 'website': 'https://oureasoft.com', 'careers': 'https://oureasoft.com/careers'},
            {'name': 'Litmus7 Systems Consulting', 'website': 'https://www.litmus7.com', 'careers': 'https://www.litmus7.com/careers'},
            {'name': 'Spiderworks Technologies', 'website': 'https://www.spiderworks.in', 'careers': 'https://www.spiderworks.in/careers'},
            {'name': 'TechnoPark Trivandrum', 'website': 'https://www.technopark.org', 'careers': 'https://www.technopark.org'},
            {'name': 'Infopark Kochi', 'website': 'https://www.infoparkkochi.com', 'careers': 'https://www.infoparkkochi.com'},
            {'name': 'SunTec Web Services', 'website': 'https://www.suntecwebservices.com', 'careers': 'https://www.suntecwebservices.com/careers'},
            {'name': 'Cubet Techno Labs', 'website': 'https://cubettech.com', 'careers': 'https://cubettech.com/careers'},
            {'name': 'Aufait Technologies', 'website': 'https://aufaittech.com', 'careers': 'https://aufaittech.com/careers'},
            {'name': 'Sysintelli Solutions', 'website': 'https://www.sysintellisolutions.com', 'careers': 'https://www.sysintellisolutions.com/careers'},
            {'name': 'Perfomatix Solutions', 'website': 'https://www.perfomatix.com', 'careers': 'https://www.perfomatix.com/careers'},
            {'name': 'Mindster', 'website': 'https://mindster.com', 'careers': 'https://mindster.com/careers'},
            {'name': 'Techware Lab', 'website': 'https://www.techwarelab.com', 'careers': 'https://www.techwarelab.com/careers'},
            {'name': 'Softroniics', 'website': 'https://softroniics.com', 'careers': 'https://softroniics.com/careers'},
            {'name': 'Epixel Solutions', 'website': 'https://www.epixelsoft.com', 'careers': 'https://www.epixelsoft.com/careers'},
            {'name': 'Innoppl Technologies', 'website': 'https://www.innoppl.com', 'careers': 'https://www.innoppl.com/careers'},
            {'name': 'Cabot Solutions', 'website': 'https://www.cabotsolutions.com', 'careers': 'https://www.cabotsolutions.com/careers'},
            {'name': 'Cyberpark Kozhikode', 'website': 'https://www.cyberparkkerala.org', 'careers': 'https://www.cyberparkkerala.org'},
            {'name': 'KINFRA Techno Industrial Park', 'website': 'https://www.kinfra.org', 'careers': 'https://www.kinfra.org/careers'},
            {'name': 'GTech - Group of Technology Companies', 'website': 'https://www.gtechonline.in', 'careers': 'https://www.gtechonline.in/careers'},
            {'name': 'Manappuram Fintech', 'website': 'https://www.manappuram.com', 'careers': 'https://www.manappuram.com/careers'},
            {'name': 'Federal Bank Technology', 'website': 'https://www.federalbank.co.in', 'careers': 'https://www.federalbank.co.in/careers'},
            {'name': 'South Indian Bank IT', 'website': 'https://www.southindianbank.com', 'careers': 'https://www.southindianbank.com/careers'},
            {'name': 'Muthoot Finance Tech', 'website': 'https://www.muthootfinance.com', 'careers': 'https://www.muthootfinance.com/careers'},
            # Web Development & Digital Agencies
            {'name': 'Codemaker', 'website': 'https://codemaker.in', 'careers': 'https://codemaker.in/careers'},
            {'name': 'Webandcrafts', 'website': 'https://webandcrafts.com', 'careers': 'https://webandcrafts.com/careers'},
            {'name': 'Intertoons Internet Services', 'website': 'https://www.intertoons.com', 'careers': 'https://www.intertoons.com/careers'},
            {'name': 'Iroid Technologies', 'website': 'https://www.iroidtechnologies.com', 'careers': 'https://www.iroidtechnologies.com/careers'},
            {'name': 'Appinventiv Kochi', 'website': 'https://appinventiv.com', 'careers': 'https://appinventiv.com/careers'},
            {'name': 'Aufait UX', 'website': 'https://aufaitux.com', 'careers': 'https://aufaitux.com/careers'},
            {'name': 'Webdura Technologies', 'website': 'https://webdura.com', 'careers': 'https://webdura.com/careers'},
            {'name': 'Mindmade Technologies', 'website': 'https://www.mindmade.in', 'careers': 'https://www.mindmade.in/careers'},
            {'name': 'Techspawn Solutions', 'website': 'https://techspawn.com', 'careers': 'https://techspawn.com/careers'},
            {'name': 'LogiQ Apps', 'website': 'https://logiqapps.com', 'careers': 'https://logiqapps.com/careers'},
            {'name': 'Trogon Media', 'website': 'https://trogonmedia.com', 'careers': 'https://trogonmedia.com/careers'},
            {'name': 'Riafy Technologies', 'website': 'https://riafy.com', 'careers': 'https://riafy.com/careers'},
            {'name': 'Zesty Beanz Technologies', 'website': 'https://www.zestybeanz.com', 'careers': 'https://www.zestybeanz.com/careers'},
            {'name': 'Raweng Technologies', 'website': 'https://raweng.com', 'careers': 'https://raweng.com/careers'},
            {'name': 'LogidotsLabs', 'website': 'https://logidots.com', 'careers': 'https://logidots.com/careers'},
            # Startups & Product Companies
            {'name': 'Agrima Infotech', 'website': 'https://www.agrimainfotech.com', 'careers': 'https://www.agrimainfotech.com/careers'},
            {'name': 'Foradian Technologies', 'website': 'https://foradian.com', 'careers': 'https://foradian.com/careers'},
            {'name': 'Genrobotics', 'website': 'https://genrobotics.com', 'careers': 'https://genrobotics.com/careers'},
            {'name': 'NASSCOM Kerala', 'website': 'https://community.nasscom.in', 'careers': 'https://community.nasscom.in/kerala'},
            {'name': 'Kerala Startup Mission', 'website': 'https://startupmission.kerala.gov.in', 'careers': 'https://startupmission.kerala.gov.in'},
            {'name': 'Maker Village', 'website': 'https://www.makervillage.in', 'careers': 'https://www.makervillage.in/careers'},
            {'name': 'BEPIC IT Solutions', 'website': 'https://bepicit.com', 'careers': 'https://bepicit.com/careers'},
            {'name': 'Steyp Technologies', 'website': 'https://steyp.com', 'careers': 'https://steyp.com/careers'},
            {'name': 'ThinkPalm Technologies', 'website': 'https://thinkpalm.com', 'careers': 'https://thinkpalm.com/careers'},
            {'name': 'Rapidor Technologies', 'website': 'https://rapidor.co', 'careers': 'https://rapidor.co/careers'},
            {'name': 'SocialBee AI', 'website': 'https://socialbee.ai', 'careers': 'https://socialbee.ai/careers'},
            # Healthcare IT
            {'name': 'Aurion Pro Kerala', 'website': 'https://www.aurionpro.com', 'careers': 'https://www.aurionpro.com/careers'},
            {'name': 'DocOnline', 'website': 'https://www.doconline.com', 'careers': 'https://www.doconline.com/careers'},
            {'name': 'Practo Kerala', 'website': 'https://www.practo.com', 'careers': 'https://www.practo.com/company/careers'},
            # EdTech
            {'name': 'Entri', 'website': 'https://entri.app', 'careers': 'https://entri.app/careers'},
            {'name': 'Geeksynergy Technologies', 'website': 'https://geeksynergy.com', 'careers': 'https://geeksynergy.com/careers'},
            {'name': 'Camp K12 Kerala', 'website': 'https://campk12.com', 'careers': 'https://campk12.com/careers'},
            # E-commerce & Retail Tech
            {'name': 'Lulu Group IT', 'website': 'https://www.lulugroupinternational.com', 'careers': 'https://www.lulugroupinternational.com/careers'},
            {'name': 'Malabar Gold IT', 'website': 'https://www.malabargoldanddiamonds.com', 'careers': 'https://www.malabargoldanddiamonds.com/careers'},
            {'name': 'Kalyan Jewellers Tech', 'website': 'https://www.kalyanjewellers.net', 'careers': 'https://www.kalyanjewellers.net/careers'},
            # Additional IT Services
            {'name': 'Sutherland Kerala', 'website': 'https://www.sutherlandglobal.com', 'careers': 'https://www.sutherlandglobal.com/careers'},
            {'name': 'Concentrix Kochi', 'website': 'https://www.concentrix.com', 'careers': 'https://www.concentrix.com/careers'},
            {'name': 'CSS Corp Kerala', 'website': 'https://www.csscorp.com', 'careers': 'https://www.csscorp.com/careers'},
            {'name': 'Hexaware Kerala', 'website': 'https://hexaware.com', 'careers': 'https://hexaware.com/careers'},
            {'name': 'Cyient Kerala', 'website': 'https://www.cyient.com', 'careers': 'https://www.cyient.com/careers'},
            {'name': 'LTIMindtree Kerala', 'website': 'https://www.ltimindtree.com', 'careers': 'https://www.ltimindtree.com/careers'},
            {'name': 'NIIT Technologies Kerala', 'website': 'https://www.niit-tech.com', 'careers': 'https://www.niit-tech.com/careers'},
            {'name': 'Mphasis Kerala', 'website': 'https://www.mphasis.com', 'careers': 'https://www.mphasis.com/careers'},
            {'name': 'Mindtree Kochi', 'website': 'https://www.mindtree.com', 'careers': 'https://www.mindtree.com/careers'},
            {'name': 'BORN Group Kerala', 'website': 'https://www.borngroup.com', 'careers': 'https://www.borngroup.com/careers'},
            # Cloud & DevOps
            {'name': 'CloudDrove Technologies', 'website': 'https://clouddrove.com', 'careers': 'https://clouddrove.com/careers'},
            {'name': 'Poornam Infovision', 'website': 'https://poornaminfo.com', 'careers': 'https://poornaminfo.com/careers'},
            {'name': 'Bobcares', 'website': 'https://bobcares.com', 'careers': 'https://bobcares.com/careers'},
            # Data & Analytics
            {'name': 'TheMathCompany Kerala', 'website': 'https://themathcompany.com', 'careers': 'https://themathcompany.com/careers'},
            {'name': 'Gramener Kerala', 'website': 'https://gramener.com', 'careers': 'https://gramener.com/careers'},
            {'name': 'Mu Sigma Kerala', 'website': 'https://www.mu-sigma.com', 'careers': 'https://www.mu-sigma.com/careers'},
            # More Infopark Companies
            {'name': 'Accel Frontline Kerala', 'website': 'https://www.accelya.com', 'careers': 'https://www.accelya.com/careers'},
            {'name': 'NTT Ltd Kerala', 'website': 'https://hello.global.ntt', 'careers': 'https://hello.global.ntt/careers'},
            {'name': 'DXC Technology Kerala', 'website': 'https://www.dxc.technology', 'careers': 'https://www.dxc.technology/careers'},
            {'name': 'LTI Kerala', 'website': 'https://www.lntinfotech.com', 'careers': 'https://www.lntinfotech.com/careers'},
            {'name': 'Firstsource Kerala', 'website': 'https://www.firstsource.com', 'careers': 'https://www.firstsource.com/careers'},
        ],
        'india': [
            # Top Unicorns & Decacorns
            {'name': 'Freshworks', 'website': 'https://www.freshworks.com', 'careers': 'https://www.freshworks.com/company/careers'},
            {'name': 'Zoho', 'website': 'https://www.zoho.com', 'careers': 'https://careers.zoho.com'},
            {'name': 'Flipkart', 'website': 'https://www.flipkart.com', 'careers': 'https://www.flipkartcareers.com'},
            {'name': 'Paytm', 'website': 'https://paytm.com', 'careers': 'https://jobs.paytm.com'},
            {'name': 'Razorpay', 'website': 'https://razorpay.com', 'careers': 'https://razorpay.com/jobs'},
            {'name': 'Swiggy', 'website': 'https://www.swiggy.com', 'careers': 'https://careers.swiggy.com'},
            {'name': 'Zomato', 'website': 'https://www.zomato.com', 'careers': 'https://www.zomato.com/careers'},
            {'name': 'CRED', 'website': 'https://cred.club', 'careers': 'https://careers.cred.club'},
            {'name': 'PhonePe', 'website': 'https://www.phonepe.com', 'careers': 'https://www.phonepe.com/careers'},
            {'name': 'Ola', 'website': 'https://www.olacabs.com', 'careers': 'https://www.olacabs.com/careers'},
            {'name': 'Meesho', 'website': 'https://meesho.com', 'careers': 'https://meesho.io/careers'},
            {'name': 'Byju\'s', 'website': 'https://byjus.com', 'careers': 'https://byjus.com/careers'},
            {'name': 'Unacademy', 'website': 'https://unacademy.com', 'careers': 'https://unacademy.com/careers'},
            {'name': 'Postman', 'website': 'https://www.postman.com', 'careers': 'https://www.postman.com/company/careers'},
            {'name': 'Hasura', 'website': 'https://hasura.io', 'careers': 'https://hasura.io/careers'},
            {'name': 'Chargebee', 'website': 'https://www.chargebee.com', 'careers': 'https://www.chargebee.com/careers'},
            {'name': 'Druva', 'website': 'https://www.druva.com', 'careers': 'https://www.druva.com/company/careers'},
            {'name': 'Browserstack', 'website': 'https://www.browserstack.com', 'careers': 'https://www.browserstack.com/careers'},
            {'name': 'MoEngage', 'website': 'https://www.moengage.com', 'careers': 'https://www.moengage.com/careers'},
            {'name': 'CleverTap', 'website': 'https://clevertap.com', 'careers': 'https://clevertap.com/careers'},
            # MNCs with India offices
            {'name': 'Atlassian India', 'website': 'https://www.atlassian.com', 'careers': 'https://www.atlassian.com/company/careers'},
            {'name': 'Microsoft India', 'website': 'https://www.microsoft.com/en-in', 'careers': 'https://careers.microsoft.com'},
            {'name': 'Google India', 'website': 'https://www.google.co.in', 'careers': 'https://careers.google.com'},
            {'name': 'Amazon India', 'website': 'https://www.amazon.in', 'careers': 'https://www.amazon.jobs/en'},
            {'name': 'Thoughtworks India', 'website': 'https://www.thoughtworks.com', 'careers': 'https://www.thoughtworks.com/careers'},
            {'name': 'Adobe India', 'website': 'https://www.adobe.com/in', 'careers': 'https://www.adobe.com/careers'},
            {'name': 'Oracle India', 'website': 'https://www.oracle.com/in', 'careers': 'https://www.oracle.com/in/careers'},
            {'name': 'SAP India', 'website': 'https://www.sap.com/india', 'careers': 'https://www.sap.com/about/careers'},
            {'name': 'IBM India', 'website': 'https://www.ibm.com/in-en', 'careers': 'https://www.ibm.com/careers'},
            {'name': 'Cisco India', 'website': 'https://www.cisco.com', 'careers': 'https://www.cisco.com/c/en/us/about/careers'},
            {'name': 'VMware India', 'website': 'https://www.vmware.com', 'careers': 'https://www.vmware.com/company/careers'},
            {'name': 'Salesforce India', 'website': 'https://www.salesforce.com', 'careers': 'https://www.salesforce.com/company/careers'},
            {'name': 'ServiceNow India', 'website': 'https://www.servicenow.com', 'careers': 'https://www.servicenow.com/careers'},
            {'name': 'Uber India', 'website': 'https://www.uber.com', 'careers': 'https://www.uber.com/in/en/careers'},
            {'name': 'LinkedIn India', 'website': 'https://www.linkedin.com', 'careers': 'https://careers.linkedin.com'},
            {'name': 'Twitter India', 'website': 'https://twitter.com', 'careers': 'https://careers.twitter.com'},
            {'name': 'Meta India', 'website': 'https://www.meta.com', 'careers': 'https://www.metacareers.com'},
            {'name': 'Apple India', 'website': 'https://www.apple.com/in', 'careers': 'https://www.apple.com/careers'},
            {'name': 'Netflix India', 'website': 'https://www.netflix.com', 'careers': 'https://jobs.netflix.com'},
            {'name': 'Spotify India', 'website': 'https://www.spotify.com', 'careers': 'https://www.lifeatspotify.com'},
            # Indian IT Giants
            {'name': 'TCS', 'website': 'https://www.tcs.com', 'careers': 'https://www.tcs.com/careers'},
            {'name': 'Infosys', 'website': 'https://www.infosys.com', 'careers': 'https://www.infosys.com/careers'},
            {'name': 'Wipro', 'website': 'https://www.wipro.com', 'careers': 'https://careers.wipro.com'},
            {'name': 'HCL Technologies', 'website': 'https://www.hcltech.com', 'careers': 'https://www.hcltech.com/careers'},
            {'name': 'Tech Mahindra', 'website': 'https://www.techmahindra.com', 'careers': 'https://careers.techmahindra.com'},
            {'name': 'LTIMindtree', 'website': 'https://www.ltimindtree.com', 'careers': 'https://www.ltimindtree.com/careers'},
            {'name': 'Cognizant India', 'website': 'https://www.cognizant.com', 'careers': 'https://careers.cognizant.com'},
            {'name': 'Capgemini India', 'website': 'https://www.capgemini.com', 'careers': 'https://www.capgemini.com/careers'},
            {'name': 'Accenture India', 'website': 'https://www.accenture.com', 'careers': 'https://www.accenture.com/in-en/careers'},
            {'name': 'Deloitte India', 'website': 'https://www2.deloitte.com/in', 'careers': 'https://www2.deloitte.com/in/en/careers'},
            {'name': 'PwC India', 'website': 'https://www.pwc.in', 'careers': 'https://www.pwc.in/careers'},
            {'name': 'KPMG India', 'website': 'https://home.kpmg/in', 'careers': 'https://home.kpmg/in/en/home/careers'},
            {'name': 'EY India', 'website': 'https://www.ey.com/en_in', 'careers': 'https://www.ey.com/en_in/careers'},
            # Fintech
            {'name': 'Groww', 'website': 'https://groww.in', 'careers': 'https://groww.in/careers'},
            {'name': 'Zerodha', 'website': 'https://zerodha.com', 'careers': 'https://zerodha.com/careers'},
            {'name': 'Upstox', 'website': 'https://upstox.com', 'careers': 'https://upstox.com/careers'},
            {'name': 'Jupiter', 'website': 'https://jupiter.money', 'careers': 'https://jupiter.money/careers'},
            {'name': 'Slice', 'website': 'https://www.sliceit.com', 'careers': 'https://www.sliceit.com/careers'},
            {'name': 'BharatPe', 'website': 'https://www.bharatpe.com', 'careers': 'https://www.bharatpe.com/careers'},
            {'name': 'Pine Labs', 'website': 'https://www.pinelabs.com', 'careers': 'https://www.pinelabs.com/careers'},
            {'name': 'Navi', 'website': 'https://navi.com', 'careers': 'https://navi.com/careers'},
            # E-commerce & Retail
            {'name': 'Amazon', 'website': 'https://www.amazon.in', 'careers': 'https://www.amazon.jobs'},
            {'name': 'Myntra', 'website': 'https://www.myntra.com', 'careers': 'https://careers.myntra.com'},
            {'name': 'Nykaa', 'website': 'https://www.nykaa.com', 'careers': 'https://www.nykaa.com/careers'},
            {'name': 'BigBasket', 'website': 'https://www.bigbasket.com', 'careers': 'https://www.bigbasket.com/careers'},
            {'name': 'Blinkit', 'website': 'https://blinkit.com', 'careers': 'https://blinkit.com/careers'},
            {'name': 'Dunzo', 'website': 'https://www.dunzo.com', 'careers': 'https://www.dunzo.com/careers'},
            {'name': 'Lenskart', 'website': 'https://www.lenskart.com', 'careers': 'https://www.lenskart.com/careers'},
            {'name': 'Purplle', 'website': 'https://www.purplle.com', 'careers': 'https://www.purplle.com/careers'},
            # Healthtech
            {'name': 'Practo', 'website': 'https://www.practo.com', 'careers': 'https://www.practo.com/company/careers'},
            {'name': '1mg', 'website': 'https://www.1mg.com', 'careers': 'https://www.1mg.com/careers'},
            {'name': 'PharmEasy', 'website': 'https://pharmeasy.in', 'careers': 'https://pharmeasy.in/careers'},
            {'name': 'Healthifyme', 'website': 'https://www.healthifyme.com', 'careers': 'https://www.healthifyme.com/careers'},
            {'name': 'Cult.fit', 'website': 'https://www.cult.fit', 'careers': 'https://www.cult.fit/cult/careers'},
            # EdTech
            {'name': 'Vedantu', 'website': 'https://www.vedantu.com', 'careers': 'https://www.vedantu.com/careers'},
            {'name': 'upGrad', 'website': 'https://www.upgrad.com', 'careers': 'https://www.upgrad.com/careers'},
            {'name': 'Eruditus', 'website': 'https://www.eruditus.com', 'careers': 'https://www.eruditus.com/careers'},
            {'name': 'Scaler', 'website': 'https://www.scaler.com', 'careers': 'https://www.scaler.com/careers'},
            {'name': 'Physics Wallah', 'website': 'https://www.pw.live', 'careers': 'https://www.pw.live/careers'},
            # SaaS & Developer Tools
            {'name': 'Freshdesk', 'website': 'https://freshdesk.com', 'careers': 'https://www.freshworks.com/company/careers'},
            {'name': 'Wingify', 'website': 'https://wingify.com', 'careers': 'https://wingify.com/careers'},
            {'name': 'WebEngage', 'website': 'https://webengage.com', 'careers': 'https://webengage.com/careers'},
            {'name': 'Haptik', 'website': 'https://www.haptik.ai', 'careers': 'https://www.haptik.ai/careers'},
            {'name': 'Yellow.ai', 'website': 'https://yellow.ai', 'careers': 'https://yellow.ai/careers'},
            {'name': 'Gupshup', 'website': 'https://www.gupshup.io', 'careers': 'https://www.gupshup.io/careers'},
            {'name': 'Sprinklr India', 'website': 'https://www.sprinklr.com', 'careers': 'https://www.sprinklr.com/careers'},
            # Cloud & Infrastructure
            {'name': 'DigitalOcean India', 'website': 'https://www.digitalocean.com', 'careers': 'https://www.digitalocean.com/careers'},
            {'name': 'Nutanix India', 'website': 'https://www.nutanix.com', 'careers': 'https://www.nutanix.com/company/careers'},
            {'name': 'Commvault India', 'website': 'https://www.commvault.com', 'careers': 'https://www.commvault.com/careers'},
            {'name': 'NetApp India', 'website': 'https://www.netapp.com', 'careers': 'https://www.netapp.com/company/careers'},
            {'name': 'Pure Storage India', 'website': 'https://www.purestorage.com', 'careers': 'https://www.purestorage.com/company/careers'},
        ],
        'bangalore': [
            {'name': 'Flipkart', 'website': 'https://www.flipkart.com', 'careers': 'https://www.flipkartcareers.com'},
            {'name': 'Razorpay', 'website': 'https://razorpay.com', 'careers': 'https://razorpay.com/jobs'},
            {'name': 'Swiggy', 'website': 'https://www.swiggy.com', 'careers': 'https://careers.swiggy.com'},
            {'name': 'Zomato', 'website': 'https://www.zomato.com', 'careers': 'https://www.zomato.com/careers'},
            {'name': 'CRED', 'website': 'https://cred.club', 'careers': 'https://careers.cred.club'},
            {'name': 'Zerodha', 'website': 'https://zerodha.com', 'careers': 'https://zerodha.com/careers'},
            {'name': 'InMobi', 'website': 'https://www.inmobi.com', 'careers': 'https://www.inmobi.com/company/careers'},
            {'name': 'Myntra', 'website': 'https://www.myntra.com', 'careers': 'https://careers.myntra.com'},
            {'name': 'Urban Company', 'website': 'https://www.urbancompany.com', 'careers': 'https://www.urbancompany.com/careers'},
            {'name': 'ShareChat', 'website': 'https://sharechat.com', 'careers': 'https://sharechat.com/careers'},
        ],
        'hyderabad': [
            {'name': 'ServiceNow India', 'website': 'https://www.servicenow.com', 'careers': 'https://www.servicenow.com/careers'},
            {'name': 'Salesforce India', 'website': 'https://www.salesforce.com', 'careers': 'https://www.salesforce.com/company/careers'},
            {'name': 'Apple India', 'website': 'https://www.apple.com/in', 'careers': 'https://www.apple.com/careers'},
            {'name': 'Qualcomm India', 'website': 'https://www.qualcomm.com', 'careers': 'https://www.qualcomm.com/company/careers'},
            {'name': 'Facebook India', 'website': 'https://www.facebook.com', 'careers': 'https://www.metacareers.com'},
            {'name': 'Deloitte India', 'website': 'https://www2.deloitte.com/in', 'careers': 'https://www2.deloitte.com/in/en/careers'},
        ],
        'chennai': [
            {'name': 'Zoho', 'website': 'https://www.zoho.com', 'careers': 'https://careers.zoho.com'},
            {'name': 'Freshworks', 'website': 'https://www.freshworks.com', 'careers': 'https://www.freshworks.com/company/careers'},
            {'name': 'Chargebee', 'website': 'https://www.chargebee.com', 'careers': 'https://www.chargebee.com/careers'},
            {'name': 'Kissflow', 'website': 'https://kissflow.com', 'careers': 'https://kissflow.com/careers'},
            {'name': 'Ather Energy', 'website': 'https://www.atherenergy.com', 'careers': 'https://www.atherenergy.com/careers'},
        ],
        'pune': [
            {'name': 'Persistent Systems', 'website': 'https://www.persistent.com', 'careers': 'https://www.persistent.com/careers'},
            {'name': 'Druva', 'website': 'https://www.druva.com', 'careers': 'https://www.druva.com/company/careers'},
            {'name': 'Icertis', 'website': 'https://www.icertis.com', 'careers': 'https://www.icertis.com/company/careers'},
            {'name': 'Pubmatic', 'website': 'https://pubmatic.com', 'careers': 'https://pubmatic.com/careers'},
        ],
    }
    
    def __init__(self):
        super().__init__(
            name="static_companies",
            base_url="",
            requires_js=False,
        )
        self.logger = get_logger()
    
    # Location aliases for better matching
    LOCATION_ALIASES = {
        'bengaluru': 'bangalore',
        'bengalore': 'bangalore',
        'blr': 'bangalore',
        'hyd': 'hyderabad',
        'mad': 'chennai',
        'madras': 'chennai',
        'bombay': 'mumbai',
        'bom': 'mumbai',
        'del': 'delhi',
        'new delhi': 'delhi',
        'ncr': 'delhi',
        'kochi': 'kerala',
        'cochin': 'kerala',
        'trivandrum': 'kerala',
        'thiruvananthapuram': 'kerala',
        'ernakulam': 'kerala',
        'kozhikode': 'kerala',
        'calicut': 'kerala',
    }
    
    def _normalize_location(self, location: str) -> str:
        """Normalize location string to match database keys."""
        location = location.lower().strip()
        
        # Check aliases first
        for alias, canonical in self.LOCATION_ALIASES.items():
            if alias in location:
                return canonical
        
        # Extract city name
        for city in self.COMPANIES_DB.keys():
            if city in location:
                return city
        return 'default'
    
    def search(
        self,
        location: str,
        roles: List[str],
        max_results: int = 100,
    ) -> Generator[Company, None, None]:
        """Return companies from the static database."""
        
        normalized = self._normalize_location(location)
        companies_list = list(self.COMPANIES_DB.get(normalized, []))
        
        # For Indian locations, also include pan-India companies
        indian_locations = ['kerala', 'bangalore', 'hyderabad', 'chennai', 'pune', 'mumbai', 'delhi']
        if normalized in indian_locations and normalized != 'india':
            india_companies = self.COMPANIES_DB.get('india', [])
            companies_list = companies_list + india_companies
        
        # Also add default (remote) companies
        if normalized != 'default':
            companies_list = companies_list + self.COMPANIES_DB.get('default', [])
        
        # Deduplicate by company name
        seen_names = set()
        unique_companies = []
        for c in companies_list:
            if c['name'].lower() not in seen_names:
                seen_names.add(c['name'].lower())
                unique_companies.append(c)
        
        self.logger.info(f"Found {len(unique_companies)} companies in static database for {location}")
        
        for i, company_data in enumerate(unique_companies):
            if i >= max_results:
                break
            
            company = Company(
                name=company_data['name'],
                location=location,
                source_url=company_data.get('careers', company_data['website']),
                website=company_data['website'],
                careers_url=company_data.get('careers'),
                hiring_roles=roles.copy(),  # Assume they're hiring for requested roles
            )
            
            yield company
    
    def get_company_details(self, company: Company) -> Company:
        """No additional enrichment needed for static source."""
        return company
