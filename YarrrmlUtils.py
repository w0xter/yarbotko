import yaml
from ast import literal_eval

import GeneralUtils as utils

class Yarrrml:
    def __init__(self, path):
        self.path = path
        self.yarrrml = {}
        self.simplifiyedYarrrml= {}
        self.__readYarrrml()
        self.__substitutePrefixes()
    def __readYarrrml(self):
        f = open(self.path, 'r', encoding='utf-8')
        self.yarrrml = yaml.load(f, Loader=yaml.FullLoader)
    def setYarrrml(self, newYarrrml):
        self.yarrrml = newYarrrml

    def getSources(self):
        result = {}
        for tm in self.yarrrml["mappings"]:
            result[tm] = self.yarrrml["mappings"]["sources"][0] # we are assuming that every TM only have one source
        return result
    def getTm(self, tm):
        if(tm in self.yarrrml["mappings"]):
            return self.yarrrml["mappings"][tm]
        else:
            raise Exception("Invalid TM name:{} is not included in the Mappnig".format(tm))

    def __substitutePrefixes(self):
        prefixes = self.yarrrml["prefixes"]
        strMapping = str(self.yarrrml['mappings'])
        for prefix in prefixes:
            strMapping = strMapping.replace('\'' + prefix + ':', '\'' + prefixes[prefix])
    #    strMapping = strMapping.replace('\'','"')
        expandedMapping  = dict(literal_eval(strMapping))
        for tm in expandedMapping:
            for index,po in enumerate(expandedMapping[tm]['po']):
                if type(po) is list and po[0] == 'a':
                    expandedMapping[tm]['po'][index][0] = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
        self.yarrrml = {'prefixes':prefixes,'mappings':dict(expandedMapping)}

    def simplifyMappingAccordingToQuery(self, uris):
        newMapping = {'prefixes':self.yarrrml['prefixes'], 'mappings':{}}
        #print('MAPPING:\n' + str(mapping).replace('\'', '"'))
        #sys.exit()
        
        if(not utils.checkEmptyUris(uris)):
            uris = self.__getTMsfromQueryUris(uris)
            for subject in uris.keys():
                for tm in uris[subject]['TMs']:
                    #print('SUBJECT:' + str(subject))
                    if(uris[subject]['fullTM']):
                        #print('***********************1*******************')
                        if(tm not in newMapping['mappings'].keys()):
                            newMapping['mappings'][tm] = {
                                'sources':self.yarrrml['mappings'][tm]['sources'],
                                's':self.yarrrml['mappings'][tm]['s'],
                                'po':[]
                                }
                        newMapping['mappings'][tm]['po'] = self.yarrrml['mappings'][tm]['po']
                        #print(str(newMapping).replace('\'', '"'))
                    else:
                        for po in self.yarrrml['mappings'][tm]['po']:
                            if(utils.isPoInUris(po, uris[subject]['uris'])):
                                #print('*****************2*******************+')
                                if(tm not in newMapping['mappings'].keys()):
                                    newMapping['mappings'][tm] = {
                                        'sources':self.yarrrml['mappings'][tm]['sources'],
                                        's':self.yarrrml['mappings'][tm]['s'],
                                        'po':[]
                                        }
                                if(po not in newMapping['mappings'][tm]['po']):
                                    newMapping['mappings'][tm]['po'].append(po)
            #print('MAPPING:\n' + str(newMapping).replace('\'', '"'))
        newMapping = self.__removeEmptyTM(newMapping)
        newMapping  = self.__addReferencesOfTheJoins(newMapping)
        self.simplifiyedYarrrml = newMapping

    def __getTMsfromQueryUris(self, uris):
        for subject in uris:
            uris[subject]['TMs'] = []
            for tm in self.yarrrml['mappings']:
                tmUris = utils.getUrisFromTM(self.yarrrml['mappings'][tm])
                if len(list(set(tmUris) & set(uris[subject]['uris']))) == len(uris[subject]['uris']):
                    uris[subject]['TMs'].append(tm)
        return uris

    def __removeEmptyTM(self, mapping):
        #print('MAPPING:\n' + str(mapping).replace('\'','"'))
        newMapping = mapping.copy()
        tmToRemove = []
        types = [ po[1] #Adding obejct if predicate is rdf:type
                for tm in mapping['mappings']
                for po in mapping['mappings'][tm]['po']
                if (type(po) is list and po[0] == 'a')
                ]
        for tm in mapping['mappings']:
            #print('PO:\n' + str(mapping['mappings'][tm]['po']))
            if(len(mapping['mappings'][tm]['po']) == 1 and
                type(mapping['mappings'][tm]['po'][0]) is list and
                mapping['mappings'][tm]['po'][0][0] == 'a'
                and types.count(mapping['mappings'][tm]['po'][0][1]) > 1):
                types.pop(types.index(mapping['mappings'][tm]['po'][0][1]))
                tmToRemove.append(tm)
        for tm in tmToRemove:
            del newMapping['mappings'][tm]
        return newMapping

    def __addReferencesOfTheJoins(self, mapping):
        #print('***************NO REFERENCES MAPPING**********:\n\n\n' + str(mapping).replace('\'', '"'))
        newMapping = {'prefixes':mapping['prefixes'], 'mappings':mapping['mappings']}
        tmReferences = {}
        for tm in mapping['mappings']:
            for po in mapping['mappings'][tm]['po']:
                if type(po) is dict:
                    for o in po['o']:
                        tmReferences.update(self.__checkIfReferenceIsDefined(tmReferences,mapping,o))
        newMapping['mappings'].update(tmReferences)
        return newMapping

    def __checkIfReferenceIsDefined(self,storedTm,mapping,o):
        newMapping = mapping.copy()
        #print('\n\nO:\n\n' + str(o))
        joinReferences = utils.getJoinReferences(o)
        tmName = o['mapping']
        #print('\n\n\nJOIN REFERENCES:\n\n\n' + str(joinReferences))
        if(tmName not in storedTm.keys()):
            storedTm[tmName] = self.yarrrml['mappings'][tmName]
            storedTm[tmName]['po'] = []
            if(tmName in mapping['mappings'].keys()):
                storedTm[tmName] = mapping['mappings'][tmName]
        if ((tmName not in newMapping['mappings'].keys() or
            joinReferences['outerRef'] not in utils.getColPatterns(newMapping['mappings'][tmName])) and
            joinReferences['outerRef'] not in utils.getColPatterns(storedTm[tmName])
                ):
            #print('BUSCAMOS:' + str(joinReferences['outerRef']))
            for i,po in enumerate(self.yarrrml['mappings'][o['mapping']]['po']):
                if(joinReferences['outerRef'] in utils.getColPatterns(po)):
                    #print('Hay que añadir a: \n' + str(po))
                    storedTm[tmName]['po'].append(po)
        return storedTm        