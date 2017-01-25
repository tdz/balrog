from auslib.AUS import isForbiddenUrl
from auslib.blobs.base import Blob
from auslib.errors import BadDataError


class SensorWebBlobV1(Blob):
    jsonschema = "sensorweb.yml"

    def __init__(self, **kwargs):
        Blob.__init__(self, **kwargs)
        if "schema_version" not in self:
            self["schema_version"] = 2000

    def getVendorsForPlatform(self, platform):
        for v in self["vendors"]:
            if platform in self["vendors"][v]["platforms"] or "default" in self["vendors"][v]["platforms"]:
                yield v

    def getResolvedPlatform(self, vendor, platform):
        if platform in self['vendors'][vendor]['platforms']:
            return self['vendors'][vendor]['platforms'][platform].get('alias', platform)
        if "default" in self['vendors'][vendor]['platforms']:
            return "default"
        raise BadDataError("No platform '%s' or default in vendor '%s'", platform, vendor)

    def getPlatformData(self, vendor, platform):
        platform = self.getResolvedPlatform(vendor, platform)
        try:
            return self['vendors'][vendor]['platforms'][platform]
        except KeyError:
            raise BadDataError("No platform '%s' in vendor '%s'", platform, vendor)

    def shouldServeUpdate(self, updateQuery):
        # SensorWeb updates should always be returned. It is the responsibility
        # of the client to decide whether or not any action needs to be taken.
        return True

    def getInnerHeaderXML(self, updateQuery, update_type, whitelistedDomains, specialForceHosts):
        return '    <sensorweb>'

    def getInnerFooterXML(self, updateQuery, update_type, whitelistedDomains, specialForceHosts):
        return '    </sensorweb>'

    # Because specialForceHosts is only relevant to our own internal servers,
    # and these type of updates are always served externally, we don't process
    # them in SensorWeb blobs.
    def getInnerXML(self, updateQuery, update_type, whitelistedDomains, specialForceHosts):
        buildTarget = updateQuery["buildTarget"]

        vendorXML = []
        for vendor in sorted(self.getVendorsForPlatform(buildTarget)):
            vendorInfo = self["vendors"][vendor]
            platformData = self.getPlatformData(vendor, buildTarget)

            url = platformData["fileUrl"]
            if isForbiddenUrl(url, updateQuery["product"], whitelistedDomains):
                continue
            vendorXML.append('        <firmware id="%s" URL="%s" hashFunction="%s" hashValue="%s" size="%s" version="%s"/>' %
                             (vendor, url, self["hashFunction"], platformData["hashValue"],
                              platformData["filesize"], vendorInfo["version"]))

        return vendorXML

    def containsForbiddenDomain(self, product, whitelistedDomains):
        """Returns True if the blob contains any file URLs that contain a
           domain that we're not allowed to serve updates to."""
        for vendor in self.get('vendors', {}).values():
            for platform in vendor.get('platforms', {}).values():
                if 'fileUrl' in platform:
                    if isForbiddenUrl(platform["fileUrl"], product, whitelistedDomains):
                        return True
        return False
