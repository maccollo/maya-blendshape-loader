import maya.cmds as cmds
import json
import os
import maya.api.OpenMaya as om
class BlendshapeExportImportTool:
    @staticmethod
    def createUI():
        windowName = "Blendshape Export Import Tool"
        if cmds.window(windowName, exists=True):
            cmds.deleteUI(windowName)

        cmds.window(windowName, title="Blendshape Export Import Tool", widthHeight=(300, 100))
        cmds.columnLayout(adjustableColumn=True)

        cmds.text(label="Select Blendshape Node:")
        
        # Blendshape node menu
        cmds.optionMenu("blendshapeNodeMenu")
        for node in BlendshapeExportImportTool.get_blendshape_nodes():
            cmds.menuItem(label=node)

        cmds.button(label="Store", command=lambda x: BlendshapeExportImportTool.storeBlendshapeWeights(cmds.optionMenu("blendshapeNodeMenu", q=True, v=True)))
        cmds.button(label="Load", command=lambda x: BlendshapeExportImportTool.loadBlendshapeWeights(cmds.optionMenu("blendshapeNodeMenu", q=True, v=True)))

        cmds.showWindow()
    @staticmethod
    def get_blendshape_nodes():
        """
        Returns a list of blendshape nodes in the scene.
        """
        return cmds.ls(type='blendShape')
    @staticmethod
    def update_target_menu(*args):
        """
        Updates the target menu based on the selected blendshape node.
        """
        blendshape_node = cmds.optionMenu("blendshapeNodeMenu", query=True, value=True)
        
        # Retrieve the existing menu items and delete them
        menu_items = cmds.optionMenu("targetMenu", query=True, itemListLong=True)
        if menu_items:
            for item in menu_items:
                cmds.deleteUI(item, menuItem=True)
    @staticmethod
    def get_blendshape_targets(blendshape_node):
        """
        Returns a list of targets for the given blendshape node.
        """
        return cmds.aliasAttr(blendshape_node, query=True)[::2]  # Skip every other entry to get target names
    @staticmethod
    def storeBlendshapeWeights(blendshapeNode):
        filePath = cmds.fileDialog2(fileMode=0, caption="Save Blendshape Weights")
        if not filePath:
            return
        filePath = filePath[0]

        data = {}
        targets = BlendshapeExportImportTool.get_blendshape_targets(blendshapeNode)
        for target in targets:
            targetData = {}
            targetIndex = BlendshapeExportImportTool.get_blendshape_target_index(blendshapeNode,target)
            weight = cmds.getAttr(f"{blendshapeNode}.w[{targetIndex}]")
            inbetween_weights, inbetween_items,target_item = BlendshapeExportImportTool.find_inbetween_weights_from_target_index(blendshapeNode, targetIndex)
            for inbetween_weight, inbetween_item in zip(inbetween_weights, inbetween_items):
                inbetween_components, inbetween_positions = BlendshapeExportImportTool.extract_inbetween_positions(blendshapeNode, targetIndex, inbetween_item)
                # Example structure, add specifics for in-between targets, vertices, offsets here
                targetData[inbetween_item] = {
                    'weight': inbetween_weight,
                    'components': inbetween_components,
                    'positions': inbetween_positions
                }
            data[target] = targetData

        with open(filePath, 'w') as file:
            json.dump(data, file, indent=4)
    @staticmethod
    def loadBlendshapeWeights(blendshapeNode):
        adjusted_target_mesh_list = []
        filePath = cmds.fileDialog2(fileMode=1, caption="Load Blendshape Weights")
        if not filePath:
            return
        filePath = filePath[0]

        if not os.path.exists(filePath):
            cmds.warning("File does not exist.")
            return

        with open(filePath, 'r') as file:
            data = json.load(file)
        cmds.warning("Cationary warning: Inbetween weights in data must match blend node.")
        for target, targetData in data.items():
            # Check if the target exists. If not, create it.
            if target in BlendshapeExportImportTool.get_blendshape_targets(blendshapeNode):
                target_index = BlendshapeExportImportTool.get_blendshape_target_index(blendshapeNode, target)
            else:
                cmds.warning(f"Target {target} not found in {blendshapeNode}. Skipping...")
                continue
            # Apply data for each in-between
            for inbetween_item, inbetween_data in targetData.items():
                inbetween_weight = inbetween_data['weight']
                inbetween_components = inbetween_data['components']
                inbetween_positions = inbetween_data['positions']
                adjusted_target_mesh = BlendshapeExportImportTool.set_inbetween_positions(blendshapeNode, target_index, inbetween_item, inbetween_components, inbetween_positions,adjusted_target_mesh_list)
                if adjusted_target_mesh:
                    adjusted_target_mesh_list.append(adjusted_target_mesh)

        cmds.inViewMessage(amg='Blendshape weights and in-betweens loaded.', pos='midCenter', fade=True)

    # Placeholder for a function that would apply vertex offsets to a target/in-between.
    # This is a complex task that involves manipulating mesh geometry directly and is not covered here.
    @staticmethod
    def find_inbetween_weights_from_target_name(blendshape_node, target_name):
        """Finds and returns the inbetween weights, inbetween items (inbetween index for the node) and target index of a blendshape target"""
        target_index = BlendshapeExportImportTool.get_blendshape_target_index(blendshape_node, target_name)
        if target_index is not None:
            inbetween_weights, inbetween_items,target_item = BlendshapeExportImportTool.find_inbetween_weights_from_target_index(blendshape_node, target_index)
            if inbetween_weights:
                return inbetween_weights, inbetween_items,target_item,target_index
        return None
    @staticmethod
    def get_blendshape_target_index(blendshape_node, target_name):
        """
        Takes the name of a blendshape target and returns the index.
        """
        alias_list = cmds.aliasAttr(blendshape_node, q=True)
        target_index = None
        for i, alias in enumerate(alias_list):
            if alias == target_name:
                target_index = i // 2  # Each target has two entries in the alias list (weight and input)
                return target_index
        #rise error if the target is not found
        raise ValueError(f"Target {target_name} not found in blendshape node {blendshape_node}.")
    @staticmethod
    def find_inbetween_weights_from_target_index(blendshape_node, target_index):
        """
        Attempt to find the inbetween weights for a specific target of a blendshape node by checking each
        inputTargetItem for available inbetween weights.
        """
        inbetween_weights = []
        inbetween_items = []
        # Attempt to query all inputTargetItems for the targetIndex
        target_items = cmds.getAttr(f'{blendshape_node}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem', multiIndices=True)
        
        if target_items:
            for item in target_items:
                weight = (item - 5000) / 1000.0  # Convert the internal weight to the actual weight
                if True or 0 < weight and weight < 1:
                    inbetween_weights.append(weight)
                    inbetween_items.append(item)
                if weight == 1:
                    target_item = item
        
        return inbetween_weights, inbetween_items, target_item
    @staticmethod
    def extract_inbetween_positions(blendshape_node, target_index, inbetween_index):
        """Takes a blendshape node, base shape, target index and inbetween index and returns the position offset of each vertex that is stored in the blendshape node."""
        # Retrieve the list of components that have been modified
        inbetween_components_attr = f'{blendshape_node}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[{inbetween_index}].inputComponentsTarget'
        modified_components = cmds.getAttr(inbetween_components_attr)
        
        # Retrieve the modified positions
        inbetween_positions_attr = f'{blendshape_node}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[{inbetween_index}].inputPointsTarget'
        modified_positions = cmds.getAttr(inbetween_positions_attr)
        return modified_components, modified_positions
    @staticmethod
    def set_inbetween_positions(blendshape_node, target_index, inbetween_index, modified_components, modified_positions,adjusted_target_mesh_list):
        """
        Sets the modified components and positions for a specific target and in-between index of a blendshape node.
        :param blendshape_node: Name of the blendshape node.
        :param target_index: Index of the target within the blendshape node.
        :param inbetween_index: The specific in-between index (6000 for base, 5000 for first in-between, etc.).
        :param modified_components: The components that have been modified, as retrieved by cmds.getAttr.
        :param modified_positions: The modified positions or offsets for these components.
        """
        #we need to check the input target item has an inputGeomTarget connection
        inputGeomTarget = f'{blendshape_node}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[{inbetween_index}].inputGeomTarget'
        if cmds.connectionInfo(inputGeomTarget, isDestination=True):
            #enter edit mode on that target
            inputGeomTarget = cmds.listConnections(inputGeomTarget, source=True)
            if inputGeomTarget[0] in adjusted_target_mesh_list:
                #this is a target that exists as a mesh and we have already adjusted it
                return None
            base_shape = BlendshapeExportImportTool.get_base_shape_from_blendshape(blendshape_node)
            return BlendshapeExportImportTool.modify_input_geom_target(inputGeomTarget,base_shape, modified_components, modified_positions,blendshape_node)

        # Attribute names for components and positions
        inbetween_components_attr = f'{blendshape_node}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[{inbetween_index}].inputComponentsTarget'
        inbetween_positions_attr = f'{blendshape_node}.inputTarget[0].inputTargetGroup[{target_index}].inputTargetItem[{inbetween_index}].inputPointsTarget'

        # Set the modified components
        if modified_components:
            cmds.setAttr(inbetween_components_attr, len(modified_components), *modified_components, type="componentList")
        # Set the modified positions
        if modified_positions:
            # Note: Ensure modified_positions is a flat list in the format [x1, y1, z1, x2, y2, z2, ...]
            point_count = len(modified_positions)  # Each point consists of 3 values (x, y, z)
            cmds.setAttr(inbetween_positions_attr, point_count, *modified_positions, type="pointArray")
        return None
    @staticmethod
    def modify_input_geom_target(inputGeomTarget,base_shape, modified_components, modified_positions,blendshape_node):

        undeformed_mesh = BlendshapeExportImportTool.duplicate_without_deformation(base_shape,blendshape_node)[0]
        bs_temp_shape = BlendshapeExportImportTool.duplicate_without_deformation(base_shape,blendshape_node)[0]
        #set the blendshape offsets
        temp_bs = cmds.blendShape(bs_temp_shape, undeformed_mesh, name='temp_bs#')[0]
        cmds.delete(bs_temp_shape)
        BlendshapeExportImportTool.set_inbetween_positions(temp_bs, 0, 6000, modified_components, modified_positions,[])
        cmds.setAttr(temp_bs + '.' + bs_temp_shape, 1)
        #cmds.delete(undeformed_mesh, constructionHistory=True)
        BlendshapeExportImportTool.set_mesh_to_match_target(undeformed_mesh,inputGeomTarget[0])
        cmds.delete(undeformed_mesh)
        return(inputGeomTarget[0])
    @staticmethod
    def set_mesh_to_match_target(source_mesh, target_mesh):
        """
        Sets the target mesh to exactly match the source mesh using the OpenMaya 2.0 API.
        Both meshes must have the same topology.

        :param source_mesh: The name of the source mesh (str)
        :param target_mesh: The name of the target mesh (str)
        """
        # Get MObject for the source mesh
        selectionList = om.MSelectionList()
        selectionList.add(source_mesh)
        source_node = selectionList.getDagPath(0)
        source_fnMesh = om.MFnMesh(source_node)

        # Get MObject for the target mesh
        selectionList.clear()
        selectionList.add(target_mesh)
        target_node = selectionList.getDagPath(0)
        target_fnMesh = om.MFnMesh(target_node)

        # Get vertex positions from the source mesh
        source_positions = source_fnMesh.getPoints(om.MSpace.kObject)

        # Set vertex positions on the target mesh
        target_fnMesh.setPoints(source_positions, om.MSpace.kObject)    
    @staticmethod
    def get_base_shape_from_blendshape(blendshape_node):
        """
        Retrieves the base shape connected to the specified blendshape node.
        """
        # Find the geometry connected as input to the blendshape node
        connections = cmds.listConnections(blendshape_node + '.outputGeometry', source=False, destination=True)
        if connections:
            #check if the connection is a shape node
            for connection in connections:
                if cmds.nodeType(connection) == 'transform':
                    return connection
                else:
                    #If not we continue to the next connection
                    return BlendshapeExportImportTool.get_base_shape_from_blendshape(connection)

        else:
            cmds.warning("No base shape found for blendshape node: " + blendshape_node)
            return None
    @staticmethod
    def duplicate_without_deformation(mesh_name,blendshape_node, name = None, unlock_channels = True):
        """Turns off all deformers on the mesh, duplicates it, then turns the deformers back on and returns the duplicated mesh. The unlock channels arguments will unlock the transforms"""
        if not name:
            name = mesh_name + '#'
        history = cmds.listHistory(mesh_name)

        nodes_to_turn_back_on = []
        nodes_envelope_value = []
        for node in history:
            if cmds.attributeQuery('envelope', node=node, exists=True):
                nodes_to_turn_back_on.append(node)
                nodes_envelope_value.append(cmds.getAttr(f'{node}.envelope'))
                cmds.setAttr(f'{node}.envelope', 0)
                if node == blendshape_node:
                    break

        duplicated_mesh = cmds.duplicate(mesh_name, name = name)
        #loop over the nodes to turn back on and reset them to their original value
        for i, node in enumerate(nodes_to_turn_back_on):
            cmds.setAttr(f'{node}.envelope', nodes_envelope_value[i])
        if unlock_channels:
            cmds.setAttr(duplicated_mesh[0] + '.tx', lock=False)
            cmds.setAttr(duplicated_mesh[0] + '.ty', lock=False)
            cmds.setAttr(duplicated_mesh[0] + '.tz', lock=False)
            cmds.setAttr(duplicated_mesh[0] + '.rx', lock=False)
            cmds.setAttr(duplicated_mesh[0] + '.ry', lock=False)
            cmds.setAttr(duplicated_mesh[0] + '.rz', lock=False)
            cmds.setAttr(duplicated_mesh[0] + '.sx', lock=False)
            cmds.setAttr(duplicated_mesh[0] + '.sy', lock=False)
            cmds.setAttr(duplicated_mesh[0] + '.sz', lock=False)
        return duplicated_mesh
BlendshapeExportImportTool.createUI()
