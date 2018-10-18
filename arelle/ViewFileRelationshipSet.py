'''
Created on Oct 6, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from arelle import ModelObject, ModelDtsObject, XbrlConst, XmlUtil, ViewFile
from arelle.ModelDtsObject import ModelRelationship
from arelle.ViewFile import NOOUT, CSV, XLSX, HTML, XML, JSON 
from arelle.ViewUtil import viewReferences
from arelle.XbrlConst import conceptNameLabelRole
from arelle.ModelRenderingObject import ModelEuAxisCoord, ModelRuleDefinitionNode
from arelle.ModelFormulaObject import Aspect

import os

def viewRelationshipSet(modelXbrl, outfile, header, arcrole, linkrole=None, linkqname=None, arcqname=None, labelrole=None, lang=None):
    modelXbrl.modelManager.showStatus(_("viewing relationships {0}").format(os.path.basename(arcrole)))
    view = ViewRelationshipSet(modelXbrl, outfile, header, labelrole, lang)
    view.view(arcrole, linkrole, linkqname, arcqname)
    view.close()
    
COL_WIDTHS = {
    "Presentation Relationships":80, "Pref. Label":16, "Type": 16, "References":120,
    "Calculation Relationships": 80, "Weight": 16, "Balance": 16,
    "Dimensions Relationships": 80, "Arcrole": 32,"CntxElt": 12,"Closed": 8,"Usable": 8,
    "Resource Relationships": 80, "Arcrole": 32,"Resource": 50,"ResourceRole": 32,"Language": 20,
    "Table Relationships": 80, "Axis": 28, "Abs": 16, "Mrg": 16, "Header": 50, "Primary Item": 30, "Dimensions": 50
    }

class ViewRelationshipSet(ViewFile.View):
    def __init__(self, modelXbrl, outfile, header, labelrole, lang):
        super(ViewRelationshipSet, self).__init__(modelXbrl, outfile, header, lang)
        self.labelrole = labelrole
        self.isResourceArcrole = False
        
    def view(self, arcrole, linkrole=None, linkqname=None, arcqname=None):
        # determine relationships indent depth for dimensions linkbases
        # set up treeView widget and tabbed pane
        if arcrole == XbrlConst.parentChild: # extra columns
            heading = ["Presentation Relationships", "Pref. Label", "Type", "References"]
        elif arcrole == XbrlConst.summationItem:    # add columns for calculation relationships
            heading = ["Calculation Relationships", "Weight", "Balance"]
        elif arcrole == "XBRL-dimensions":    # add columns for dimensional information
            heading = ["Dimensions Relationships", "Arcrole","CntxElt","Closed","Usable"]
        elif arcrole == "Table-rendering":
            heading = ["Table Relationships", "Axis", "Abs", "Mrg", "Header", "Primary Item", "Dimensions"]
        elif isinstance(arcrole, (list,tuple)) or XbrlConst.isResourceArcrole(arcrole):
            self.isResourceArcrole = True
            self.showReferences = isinstance(arcrole, _STR_BASE) and arcrole.endswith("-reference")
            heading = ["Resource Relationships", "Arcrole","Resource","ResourceRole","Language"]
        else:
            heading = [os.path.basename(arcrole).title() + " Relationships"]
        # relationship set based on linkrole parameter, to determine applicable linkroles
        relationshipSet = self.modelXbrl.relationshipSet(arcrole, linkrole, linkqname, arcqname)

        self.arcrole = arcrole
        self.maxNumDims = 1
            
        if relationshipSet:
            # sort URIs by definition
            linkroleUris = []
            for linkroleUri in relationshipSet.linkRoleUris:
                modelRoleTypes = self.modelXbrl.roleTypes.get(linkroleUri)
                if modelRoleTypes:
                    roledefinition = (modelRoleTypes[0].genLabel(lang=self.lang, strip=True) or modelRoleTypes[0].definition or linkroleUri)                    
                else:
                    roledefinition = linkroleUri
                linkroleUris.append((roledefinition, linkroleUri))
            linkroleUris.sort()
    
            for roledefinition, linkroleUri in linkroleUris:
                linkRelationshipSet = self.modelXbrl.relationshipSet(arcrole, linkroleUri, linkqname, arcqname)
                for rootConcept in linkRelationshipSet.rootConcepts:
                    self.treeDepth(rootConcept, rootConcept, 2, arcrole, linkRelationshipSet, set())

        # avoid use of lastColSpan, html and excel do not use multiple cols for dimensions for now
        #if "Dimensions" == heading[-1]:
        #    lastColSpan = self.maxNumDims
        #else:
        lastColSpan = None
                    
        self.addRow(heading, asHeader=True, lastColSpan=lastColSpan) # must do after determining tree depth
        self.setColWidths([COL_WIDTHS.get(hdg, 80 if hdg.endswith("  Relationships") else 8) for hdg in heading])
        
        if relationshipSet:
            # for each URI in definition order
            for roledefinition, linkroleUri in linkroleUris:
                #Deepak-Khopade-isdr: 15-Feb-2017 added "roleDefinition" to see it on presentation tree
                attr = {"roleUri": linkroleUri, "roleDefinition": roledefinition}
                self.addRow([roledefinition], treeIndent=0, colSpan=len(heading), 
                            xmlRowElementName="linkRole", xmlRowEltAttr=attr, xmlCol0skipElt=True)
                linkRelationshipSet = self.modelXbrl.relationshipSet(arcrole, linkroleUri, linkqname, arcqname)
                for rootConcept in linkRelationshipSet.rootConcepts:
                    self.viewConcept(rootConcept, rootConcept, "", self.labelrole, 1, arcrole, linkRelationshipSet, set())

    def treeDepth(self, concept, modelObject, indent, arcrole, relationshipSet, visited):
        if concept is None:
            return
        if indent > self.treeCols: self.treeCols = indent
        if concept not in visited:
            visited.add(concept)
            childRelationshipSet = relationshipSet
            if isinstance(modelObject, ModelRelationship):
                if arcrole == "XBRL-dimensions": 
                    childRelationshipSet = self.modelXbrl.relationshipSet(XbrlConst.consecutiveArcrole.get(modelObject.arcrole,"XBRL-dimensions"),
                                                                          modelObject.linkrole)
                elif self.arcrole == "Table-rendering" and isinstance(concept, (ModelEuAxisCoord, ModelRuleDefinitionNode)):
                    numDims = len(concept.aspectValue(None, Aspect.DIMENSIONS, inherit=False) or ()) * 2
                    if numDims > self.maxNumDims: self.maxNumDims = numDims
            for modelRel in childRelationshipSet.fromModelObject(concept):
                targetRole = modelRel.targetRole
                if targetRole is None or len(targetRole) == 0:
                    targetRole = relationshipSet.linkrole
                    nestedRelationshipSet = relationshipSet
                else:
                    nestedRelationshipSet = self.modelXbrl.relationshipSet(childRelationshipSet.arcrole, targetRole)
                self.treeDepth(modelRel.toModelObject, modelRel, indent + 1, arcrole, nestedRelationshipSet, visited)
            visited.remove(concept)
            
    def viewConcept(self, concept, modelObject, labelPrefix, preferredLabel, indent, arcrole, relationshipSet, visited):
        try:
            if concept is None:
                return
            isRelation = isinstance(modelObject, ModelRelationship)
            childRelationshipSet = relationshipSet
            if isinstance(concept, ModelDtsObject.ModelConcept):
                text = labelPrefix + concept.label(preferredLabel,lang=self.lang,linkroleHint=relationshipSet.linkrole)
                if (self.arcrole in ("XBRL-dimensions", XbrlConst.hypercubeDimension) and
                    concept.isTypedDimension and 
                    concept.typedDomainElement is not None):
                    text += " (typedDomain={0})".format(concept.typedDomainElement.qname)  
                xmlRowElementName = "concept"
                #Deepak.Khopade@gmail.com: 15-Feb-2017 - start
                # added "id", "name",  "abstract", "substitutionGroup", 
                # "dataType", "nillable", "perioType", "balanceType" and "preferredLabel" so that can be imported to database
                namespace = ""

                if (str(concept.id) is not None):
                    splitted = str(concept.id).split("_")
                    if (len(splitted) > 1):
                        namespace = splitted[0]
                        
                attr = {
                    "namespace": namespace,
                    "name": str(concept.name),
                    "abstract": str(concept.abstract),
                    "substitutionGroup": str(concept.substitutionGroupQname),
                    "dataType": str(concept.typeQname),
                    "nillable": str(concept.nillable),
                    "periodType": str(concept.periodType),
                    "balanceType": str(concept.balance)}
                
                if preferredLabel != XbrlConst.conceptNameLabelRole and concept.label != None:
                    attr["standardLabel"] = str(concept.label(XbrlConst.standardLabel,lang=self.lang,linkroleHint=relationshipSet.linkrole))
                
                if preferredLabel != None:
                    attr["preferredLabel"] = os.path.basename(preferredLabel)
                    if preferredLabel == XbrlConst.periodStartLabel and concept.label != None:
                        attr["periodStartLabel"] = str(concept.label(XbrlConst.periodStartLabel,lang=self.lang,linkroleHint=relationshipSet.linkrole))
                    if preferredLabel == XbrlConst.periodEndLabel and concept.label != None:
                        attr["periodEndLabel"] = str(concept.label(XbrlConst.periodEndLabel,lang=self.lang,linkroleHint=relationshipSet.linkrole))
                    if preferredLabel != None and os.path.basename(preferredLabel) == "totalLabel":
                        attr["totalLabel"] = text
                
                if concept.label != None:
                    attr["documentation"] = str(concept.label(XbrlConst.documentationLabel,lang=self.lang,linkroleHint=relationshipSet.linkrole))

                if viewReferences(concept) != None and len(viewReferences(concept)) > 0:
                    attr["references"] = viewReferences(concept)

                #Deepak.Khopade@gmail.com: 15-Feb-2017 - end
            elif self.arcrole == "Table-rendering":
                text = concept.localName
                xmlRowElementName = "element"
                attr = {"label": concept.xlinkLabel}
            elif isinstance(concept, ModelDtsObject.ModelResource):
                if self.showReferences:
                    text = (concept.viewText().strip() or concept.localName)
                    attr = {"text": text,
                            "innerXml": XmlUtil.xmlstring(concept, stripXmlns=True, prettyPrint=False, contentsOnly=True)}
                else:
                    text = (concept.textValue.strip() or concept.localName)
                    attr = {"text": text}
                xmlRowElementName = "resource"
            else:   # just a resource
                text = concept.localName
                xmlRowElementName = text
            
            #Deepak.Khopade@gmail.com: 15-Feb-2017
            cols = [text, str(concept.name), str(concept.typeQname)]
            if arcrole == "XBRL-dimensions" and isRelation:
                relArcrole = modelObject.arcrole
                cols.append( os.path.basename( relArcrole ) )
                if relArcrole in (XbrlConst.all, XbrlConst.notAll):
                    cols.append( modelObject.contextElement )
                    cols.append( modelObject.closed )
                else:
                    cols.append(None)
                    cols.append(None)
                if relArcrole in (XbrlConst.dimensionDomain, XbrlConst.domainMember):
                    cols.append( modelObject.usable  )
                childRelationshipSet = self.modelXbrl.relationshipSet(XbrlConst.consecutiveArcrole.get(relArcrole,"XBRL-dimensions"),
                                                                      modelObject.consecutiveLinkrole)
            if self.arcrole == XbrlConst.parentChild: # extra columns
                if isRelation:
                    preferredLabel = modelObject.preferredLabel
                    if preferredLabel and preferredLabel.startswith("http://"):
                        preferredLabel = os.path.basename(preferredLabel)
                else:
                    preferredLabel = None
                #Deepak.Khopade@gmail.com: 15-Feb-2017 commented below 2 lines to avoid loading preferredLabel & type again
                #cols.append(preferredLabel)
                #cols.append(concept.niceType)
                #cols.append(viewReferences(concept))
            elif arcrole == XbrlConst.summationItem:
                if isRelation:
                    cols.append("{:0g} ".format(modelObject.weight))
                else:
                    cols.append("") # no weight on roots
                cols.append(concept.balance)
            elif self.isResourceArcrole: # resource columns
                if isRelation:
                    cols.append(modelObject.arcrole)
                else:
                    cols.append("") # no weight on roots
                if isinstance(concept, ModelDtsObject.ModelResource):
                    cols.append(concept.localName)
                    cols.append(concept.role or '')
                    cols.append(concept.xmlLang)
            
            #Deepak.Khopade@gmail.com: 31-Jul-2018 - remove extra columns
            del cols[1:3]

            self.addRow(cols, treeIndent=indent, xmlRowElementName=xmlRowElementName, xmlRowEltAttr=attr, xmlCol0skipElt=True)
            if concept not in visited:
                visited.add(concept)
                for modelRel in childRelationshipSet.fromModelObject(concept):
                    nestedRelationshipSet = relationshipSet
                    targetRole = modelRel.targetRole
                    if arcrole == XbrlConst.summationItem:
                        childPrefix = "({:+0g}) ".format(modelRel.weight) # format without .0 on integer weights
                    elif targetRole is None or len(targetRole) == 0:
                        targetRole = relationshipSet.linkrole
                        childPrefix = ""
                    else:
                        nestedRelationshipSet = self.modelXbrl.relationshipSet(childRelationshipSet.arcrole, targetRole)
                        childPrefix = "(via targetRole) "
                    toConcept = modelRel.toModelObject
                    if toConcept in visited:
                        childPrefix += "(loop) "
                    labelrole = modelRel.preferredLabel
                    if not labelrole or self.labelrole == conceptNameLabelRole: 
                        labelrole = self.labelrole
                    self.viewConcept(toConcept, modelRel, childPrefix, labelrole, indent + 1, arcrole, nestedRelationshipSet, visited)
                visited.remove(concept)
        except AttributeError: #  bad relationship
            return