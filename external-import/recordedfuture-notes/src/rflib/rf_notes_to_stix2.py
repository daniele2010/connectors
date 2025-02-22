"""
############################## TERMS OF USE ####################################
# The following code is provided for demonstration purposes only, and should   #
# not be used without independent verification. Recorded Future makes no       #
# representations or warranties, express, implied, statutory, or otherwise,    #
# regarding this code, and provides it strictly "as-is".                       #
# Recorded Future shall not be liable for, and you assume all risk of          #
# using the foregoing.                                                         #
################################################################################
"""

from datetime import datetime

import pycti  # type: ignore
import stix2

TLP_MAP = {
    "white": stix2.TLP_WHITE,
    "green": stix2.TLP_GREEN,
    "amber": stix2.TLP_AMBER,
    "red": stix2.TLP_RED,
}
{}


class ConversionError(Exception):
    """Generic exception for stix2 conversion issues"""

    pass


class RFStixEntity:
    """Parent class"""

    def __init__(self, name, type_, author):
        self.name = name
        self.type = type_
        self.author = author
        self.stix_obj = None

    def to_stix_objects(self):
        """Returns a list of STIX objects"""
        if not self.stix_obj:
            self.create_stix_objects()
        return [self.stix_obj]

    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        pass

    def to_stix_bundle(self):
        """Returns STIX objects as a Bundle"""
        return stix2.Bundle(objects=self.to_stix_objects(), allow_custom=True)

    def to_json_bundle(self):
        """Returns STIX Bundle as JSON"""
        return self.to_stix_bundle().serialize()


class Indicator(RFStixEntity):
    """Base class for Indicators of Compromise (IP, Hash, URL, Domain)"""

    def __init__(self, name, type_, author):
        self.name = name
        self.author = author
        self.stix_indicator = None
        self.stix_observable = None
        self.stix_relationship = None
        self.risk_score = None

    def to_stix_objects(self):
        """Returns a list of STIX objects"""
        if not (
            self.stix_indicator and self.stix_observable and self.stix_relationship
        ):
            self.create_stix_objects()
        return [self.stix_indicator, self.stix_observable, self.stix_relationship]

    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        self.stix_indicator = self._create_indicator()
        self.stix_observable = (
            self._create_obs()
        )  # pylint: disable=assignment-from-no-return
        self.stix_relationship = self._create_rel()

    def _create_indicator(self):
        """Creates and returns STIX2 indicator object"""
        return stix2.Indicator(
            id=pycti.Indicator.generate_id(self._create_pattern()),
            name=self.name,
            pattern_type="stix",
            valid_from=datetime.now(),
            pattern=self._create_pattern(),
            created_by_ref=self.author.id,
            custom_properties={
                "x_opencti_score": self.risk_score,
            },
        )
        pass

    def _create_pattern(self):
        """Creates STIX2 pattern for indicator"""
        pass

    def _create_obs(self):
        """Creates and returns STIX2 Observable"""
        pass

    def _create_rel(self):
        """Creates Relationship object linking indicator and observable"""
        return stix2.Relationship(
            id=pycti.StixCoreRelationship.generate_id(
                "based-on", self.stix_indicator.id, self.stix_observable.id
            ),
            relationship_type="based-on",
            source_ref=self.stix_indicator.id,
            target_ref=self.stix_observable.id,
            created_by_ref=self.author.id,
        )


class IPAddress(Indicator):
    """Converts IP address to IP indicator and observable"""

    # TODO: add ipv6 compatibility
    def _create_pattern(self):
        return f"[ipv4-addr:value = '{self.name}']"

    def _create_obs(self):
        return stix2.IPv4Address(value=self.name)


class Domain(Indicator):
    """Converts Domain to Domain indicator and observable"""

    def _create_pattern(self):
        return f"[domain-name:value = '{self.name}']"

    def _create_obs(self):
        return stix2.DomainName(value=self.name)


class URL(Indicator):
    """Converts URL to URL indicator and observable"""

    def _create_pattern(self):
        ioc = self.name.replace("\\", "\\\\")
        ioc = ioc.replace("'", "\\'")
        return f"[url:value = '{ioc}']"

    def _create_obs(self):
        return stix2.URL(value=self.name)


class FileHash(Indicator):
    """Converts Hash to File indicator and observable"""

    def __init__(self, name, type_, author):
        super().__init__(name, type_, author)
        self.algorithm = self._determine_algorithm()

    def _determine_algorithm(self):
        """Determine file hash algorithm from length"""
        if len(self.name) == 64:
            return "SHA-256"
        elif len(self.name) == 40:
            return "SHA-1"
        elif len(self.name) == 32:
            return "MD5"
        msg = (
            f"Could not determine hash type for {self.name}. Only MD5, SHA1"
            " and SHA256 hashes are supported"
        )
        raise ConversionError(msg)

    def _create_pattern(self):
        return f"[file:hashes.'{self.algorithm}' = '{self.name}']"

    def _create_obs(self):
        return stix2.File(hashes={self.algorithm: self.name})


class TLPMarking(RFStixEntity):
    """Creates TLP marking for report"""

    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        self.stix_obj = stix2.AttackPattern(
            id=pycti.AttackPattern.generate_id(self.name, self.name),
            name=self.name,
            created_by_ref=self.author.id,
            custom_properties={"x_mitre_id": self.name},
        )


class TTP(RFStixEntity):
    """Converts MITRE T codes to AttackPattern"""

    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        self.stix_obj = stix2.AttackPattern(
            id=pycti.AttackPattern.generate_id(self.name, self.name),
            name=self.name,
            created_by_ref=self.author.id,
            custom_properties={"x_mitre_id": self.name},
        )


class Identity(RFStixEntity):
    """Converts various RF entity types to a STIX2 Identity"""

    type_to_class = {
        "Company": "organization",
        "Organization": "organization",
        "Person": "individual",
        "Industry": "class",
    }

    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        self.stix_obj = stix2.Identity(
            id=pycti.Identity.generate_id(self.name, self.create_id_class()),
            name=self.name,
            identity_class=self.create_id_class(),
            created_by_ref=self.author.id,
        )

    def create_id_class(self):
        """Creates a STIX2 identity class"""
        return self.type_to_class[self.type]


class ThreatActor(RFStixEntity):
    """Converts various RF Threat Actor Organization to a STIX2 Threat Actor"""

    type_to_class = {
        "Company": "organization",
        "Organization": "organization",
        "Person": "individual",
    }

    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        self.stix_obj = stix2.ThreatActor(
            id=pycti.ThreatActor.generate_id(self.name),
            name=self.name,
            created_by_ref=self.author.id,
        )

    def create_id_class(self):
        """Creates a STIX2 identity class"""
        return self.type_to_class[self.type]


class IntrusionSet(RFStixEntity):
    """Converts Threat Actor to Intrusion Set SDO"""

    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        self.stix_obj = stix2.IntrusionSet(
            id=pycti.IntrusionSet.generate_id(self.name),
            name=self.name,
            created_by_ref=self.author.id,
        )


class Malware(RFStixEntity):
    """Converts Malware to a Malware SDO"""

    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        self.stix_obj = stix2.Malware(
            id=pycti.Malware.generate_id(self.name),
            name=self.name,
            is_family=False,
            created_by_ref=self.author.id,
        )


class Vulnerability(RFStixEntity):
    """Converts a CyberVulnerability to a Vulnerability SDO"""

    # TODO: add vuln descriptions
    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        self.stix_obj = stix2.Vulnerability(
            id=pycti.Vulnerability.generate_id(self.name),
            name=self.name,
            created_by_ref=self.author.id,
        )


class DetectionRule(RFStixEntity):
    """Represents a Yara, Sigma or SNORT rule"""

    def __init__(self, name, type_, content, author):
        # TODO: possibly need to accomodate multi-rule. Right now just shoving everything in one

        self.name = name.split(".")[0]
        self.type = type_
        self.content = content
        self.stix_obj = None
        self.author = author

        if self.type not in ("yara", "snort", "sigma"):
            msg = f"Detection rule of type {self.type} is not supported"
            raise ConversionError(msg)

    def create_stix_objects(self):
        """Creates STIX objects from object attributes"""
        self.stix_obj = stix2.Indicator(
            id=pycti.Indicator.generate_id(self.content),
            name=self.name,
            pattern_type=self.type,
            pattern=self.content,
            valid_from=datetime.now(),
            created_by_ref=self.author.id,
        )


class Software(RFStixEntity):
    def __init__(self, name, type_, author):
        self.name = name
        self.software_object = None

    def to_stix_objects(self):
        """Returns a list of STIX objects"""
        if not self.software_object:
            self.create_stix_objects()
        return [self.software_object]

    def create_stix_objects(self):
        self.software_object = stix2.Software(
            name=self.name,
        )


class Location(RFStixEntity):
    rf_type_to_stix = {
        "Country": "Country",
        "City": "City",
        "ProvinceOrState": "Administrative-Area",
    }

    def __init__(self, name, type_, author):
        self.name = name
        self.type = self.rf_type_to_stix[type_]
        self.location_object = None

    def to_stix_objects(self):
        """Returns a list of STIX objects"""
        if not self.location_object:
            self.create_stix_objects()
        return [self.location_object]

    def create_stix_objects(self):
        self.location_object = stix2.Location(
            name=self.name,
            country=self.name,
            custom_properties={"x_opencti_location_type": self.type},
        )


class Campaign(RFStixEntity):
    def __init__(self, name, type_, author):
        self.name = name
        self.campaign_object = None

    def to_stix_objects(self):
        """Returns a list of STIX objects"""
        if not self.campaign_object:
            self.create_stix_objects()
        return [self.campaign_object]

    def create_stix_objects(self):
        self.campaign_object = stix2.Campaign(
            name=self.name,
        )


# maps RF types to the corresponding python object
ENTITY_TYPE_MAPPER = {
    "IpAddress": IPAddress,
    "InternetDomainName": Domain,
    "URL": URL,
    "Hash": FileHash,
    "MitreAttackIdentifier": TTP,
    "Company": Identity,
    "Person": Identity,
    "Organization": Identity,
    "Malware": Malware,
    "CyberVulnerability": Vulnerability,
    "Product": Software,
    "Country": Location,
    "City": Location,
    "ProvinceOrState": Location,
    "Industry": Identity,
    "Operation": Campaign,
}

# maps RF types to the corresponding url to get the risk score
INDICATOR_TYPE_URL_MAPPER = {
    "IpAddress": "ip",
    "InternetDomainName": "domain",
    "URL": "url",
    "Hash": "hash",
}


class StixNote:
    """Represents Analyst Note"""

    report_type_mapper = {
        "Actor Profile": "Threat-Actor",
        "Analyst On-Demand Report": "Threat-Report",
        "Cyber Threat Analysis": "Threat-Report",
        "Flash Report": "Threat-Report",
        "Geopolitical Flash Event": "Threat-Report",
        "Geopolitical Intelligence Summary": "Threat-Report",
        "Geopolitical Profile": "Threat-Actor",
        "Geopolitical Threat Forecast": "Threat-Actor",
        "Geopolitical Validated Event": "Observed-Data",
        "Hunting Package": "Attack-Pattern",
        "Indicator": "Indicator",
        "Informational": "Threat-Report",
        "Insikt Research Lead": "Intrusion-Set",
        "Malware/Tool Profile": "Malware",
        "Regular Vendor Vulnerability Disclosures": "Vulnerability",
        "Sigma Rule": "Attack-Pattern",
        "SNORT Rule": "Indicator",
        "Source Profile": "Observed-Data",
        "The Record by Recorded Future": "Threat-Report",
        "Threat Lead": "Threat-Actor",
        "TTP Instance": "Attack-Pattern",
        "Validated Intelligence Event": "Observed-Data",
        "Weekly Threat Landscape": "Threat-Report",
        "YARA Rule": "Indicator",
    }

    def __init__(
        self,
        opencti_helper,
        tas,
        rfapi,
        tlp="white",
        person_to_ta=False,
        ta_to_intrusion_set=False,
        risk_as_score=False,
        risk_threshold=None,
    ):
        self.author = self._create_author()
        self.name = None
        self.text = None
        self.published = datetime.now()
        self.labels = None
        self.report_types = None
        self.external_references = []
        self.objects = []
        self.helper = opencti_helper
        self.tas = tas
        self.person_to_ta = person_to_ta
        self.ta_to_intrusion_set = ta_to_intrusion_set
        self.risk_as_score = risk_as_score
        self.risk_threshold = risk_threshold
        self.tlp = TLP_MAP.get(tlp.lower(), None)
        self.rfapi = rfapi

    def _create_author(self):
        """Creates Recorded Future Author"""
        return stix2.Identity(
            id=pycti.Identity.generate_id("Recorded Future", "organization"),
            name="Recorded Future",
            identity_class="organization",
        )

    def _generate_external_references(self, urls):
        """Generate External references from validation urls"""
        refs = []
        for url in urls:
            external_url = url["name"]
            source_name = external_url.split("/")[2].split(".")[-2]
            refs.append({"source_name": source_name, "url": external_url})
        return refs

    def from_json(self, note):
        """Converts to STIX Bundle from JSON objects"""
        # TODO: catch errors in for loop here
        attr = note["attributes"]
        self.name = attr["title"]
        self.text = attr["text"]
        self.published = attr["published"]
        self.external_references = self._generate_external_references(
            attr.get("validation_urls", [])
        )
        self.report_types = self._create_report_types(attr.get("topic", []))
        self.labels = [topic["name"] for topic in attr.get("topic", [])]
        for entity in attr.get("note_entities", []):
            type_ = entity["type"]
            name = entity["name"]
            if self.person_to_ta and type_ == "Person":
                stix_objs = ThreatActor(name, type_, self.author).to_stix_objects()
            elif entity["id"] in self.tas:
                if self.ta_to_intrusion_set and type_ != "Person":
                    stix_objs = IntrusionSet(name, type_, self.author).to_stix_objects()
                else:
                    stix_objs = ThreatActor(name, type_, self.author).to_stix_objects()
            elif type_ == "Source":
                external_reference = {"source_name": name, "url": name}
                self.external_references.append(external_reference)
                continue
            elif type_ not in ENTITY_TYPE_MAPPER:
                msg = f"Cannot convert entity {name} to STIX2 because it is of type {type_}"
                self.helper.log_warning(msg)
                continue
            else:
                rf_object = ENTITY_TYPE_MAPPER[type_](name, type_, self.author)
                if type_ in [
                    "IpAddress",
                    "InternetDomainName",
                    "URL",
                    "Hash",
                ]:
                    risk_score = None
                    if self.risk_threshold:
                        # If a min threshold was defined, we ignore the indicator if the score is lower than the defined threshold
                        risk_score = self.rfapi.get_risk_score(
                            INDICATOR_TYPE_URL_MAPPER[type_], name
                        )
                        if risk_score < self.risk_threshold:
                            self.helper.log_info(
                                f"Ignoring entity {name} as its risk score is lower than the defined risk threshold"
                            )
                            continue
                    if self.risk_as_score:
                        # We get the risk_score if it was already set. Otherwise, we get it from the API
                        rf_object.risk_score = (
                            risk_score
                            if risk_score
                            else self.rfapi.get_risk_score(
                                INDICATOR_TYPE_URL_MAPPER[type_], name
                            )
                        )
                stix_objs = rf_object.to_stix_objects()
            self.objects.extend(stix_objs)
        if "attachment_content" in attr:
            rule = DetectionRule(
                attr["attachment"],
                attr["attachment_type"],
                attr["attachment_content"],
                self.author,
            )
            self.objects.extend(rule.to_stix_objects())

    RELATIONSHIPS_MAPPER = [
        {
            "from": "threat-actor",
            "to": [
                {"entity": "malware", "relation": "uses"},
                {"entity": "vulnerability", "relation": "targets"},
                {"entity": "attack-pattern", "relation": "uses"},
                {"entity": "location", "relation": "targets"},
                {"entity": "identity", "relation": "targets"},
            ],
        },
        {
            "from": "intrusion-set",
            "to": [
                {"entity": "malware", "relation": "uses"},
                {"entity": "vulnerability", "relation": "targets"},
                {"entity": "attack-pattern", "relation": "uses"},
                {"entity": "location", "relation": "targets"},
                {"entity": "identity", "relation": "targets"},
            ],
        },
        {
            "from": "indicator",
            "to": [
                {"entity": "malware", "relation": "indicates"},
                {"entity": "threat-actor", "relation": "indicates"},
                {"entity": "intrusion-set", "relation": "indicates"},
            ],
        },
        {
            "from": "malware",
            "to": [
                {"entity": "attack-pattern", "relation": "uses"},
                {"entity": "location", "relation": "targets"},
                {"entity": "identity", "relation": "targets"},
            ],
        },
    ]

    def _create_rel(self, from_id, to_id, relation):
        """Creates Relationship object"""
        return stix2.Relationship(
            id=pycti.StixCoreRelationship.generate_id(relation, from_id, to_id),
            relationship_type=relation,
            source_ref=from_id,
            target_ref=to_id,
            created_by_ref=self.author.id,
        )

    def create_relations(self):
        relationships = []
        for source_entity in self.objects:
            entity_possible_relationships = list(
                filter(
                    lambda obj: obj["from"] == source_entity["type"],
                    self.RELATIONSHIPS_MAPPER,
                )
            )
            if len(entity_possible_relationships) != 0:
                for to_entity in entity_possible_relationships[0]["to"]:
                    target_entities = list(
                        filter(
                            lambda obj: obj["type"] == to_entity["entity"], self.objects
                        )
                    )
                    for target_entity in target_entities:
                        if (
                            to_entity["entity"] != "identity"
                            or target_entity["identity_class"] == "class"
                        ):
                            relationships.append(
                                self._create_rel(
                                    source_entity["id"],
                                    target_entity["id"],
                                    to_entity["relation"],
                                )
                            )
        self.objects.extend(relationships)

    def _create_report_types(self, topics):
        """Converts Insikt Topics to STIX2 Report types"""
        ret = set()
        for topic in topics:
            name = topic["name"]
            if name not in self.report_type_mapper:
                self.helper.log_warning(
                    "Could not map a report type for type {}".format(name)
                )
                continue
            ret.add(self.report_type_mapper[name])
        return list(ret)

    def to_stix_objects(self):
        """Returns a list of STIX objects"""
        report = stix2.Report(
            id=pycti.Report.generate_id(self.name, self.published),
            name=self.name,
            description=self.text,
            published=self.published,
            created_by_ref=self.author.id,
            labels=self.labels,
            report_types=self.report_types,
            object_refs=[obj.id for obj in self.objects] + [self.author.id],
            external_references=self.external_references,
            object_marking_refs=self.tlp,
        )
        return self.objects + [report, self.author, self.tlp]

    def to_stix_bundle(self):
        """Returns STIX objects as a Bundle"""
        return stix2.Bundle(objects=self.to_stix_objects(), allow_custom=True)

    def to_json_bundle(self):
        """Returns STIX Bundle as JSON"""
        return self.to_stix_bundle().serialize()
