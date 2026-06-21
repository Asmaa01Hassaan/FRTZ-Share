# -*- coding: utf-8 -*-
from odoo import models, api
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class InstallmentDependencyRegistry(models.Model):
    """
    Registry that tracks which modules provide what functionality.

    This allows us to know dependencies WITHOUT hardcoding them in manifest.

    Example:
        registry.register('payment_term_installment_extension', 'payment_term_config')
        registry.register('invoice_installment_management', 'installment_creation')
        registry.is_available('installment_creation')  -> True/False
    """
    _name = 'installment.dependency.registry'
    _description = 'Installment Dependency Registry'
    _singleton = True

    # In-memory registry of module capabilities
    _in_memory_registry = defaultdict(set)

    # Capability dependency map
    _capability_dependencies = {
        'installment_creation': ['payment_term_config'],
        'installment_payment': ['installment_creation'],
        'installment_analytics': ['installment_payment'],
        'installment_rescheduling': ['installment_analytics'],
    }

    @api.model
    def register(self, module_name, capability_name):
        """
        Register that a module provides a capability.

        Args:
            module_name (str): e.g., 'payment_term_installment_extension'
            capability_name (str): e.g., 'payment_term_config'

        Returns:
            bool: True if registered successfully
        """
        try:
            self._in_memory_registry[capability_name].add(module_name)
            _logger.debug(f"Registered {module_name} for capability {capability_name}")
            return True
        except Exception as e:
            _logger.error(f"Error registering {module_name}: {str(e)}")
            return False

    @api.model
    def unregister(self, module_name, capability_name):
        """
        Unregister a capability.

        Args:
            module_name (str): Module to unregister
            capability_name (str): Capability to remove

        Returns:
            bool: True if unregistered successfully
        """
        try:
            self._in_memory_registry[capability_name].discard(module_name)
            _logger.debug(f"Unregistered {module_name} from capability {capability_name}")
            return True
        except Exception as e:
            _logger.error(f"Error unregistering {module_name}: {str(e)}")
            return False

    @api.model
    def is_available(self, capability_name):
        """
        Check if a capability is available.

        Args:
            capability_name (str): e.g., 'installment_creation'

        Returns:
            bool: True if any module provides this capability
        """
        return bool(self._in_memory_registry.get(capability_name))

    @api.model
    def get_modules_for(self, capability_name):
        """
        Get all modules providing a capability.

        Args:
            capability_name (str): Capability to check

        Returns:
            list: List of module names
        """
        return sorted(list(self._in_memory_registry.get(capability_name, set())))

    @api.model
    def get_capabilities_of(self, module_name):
        """
        Get all capabilities provided by a module.

        Args:
            module_name (str): Module to check

        Returns:
            list: List of capability names
        """
        return sorted([
            cap for cap, modules in self._in_memory_registry.items()
            if module_name in modules
        ])

    @api.model
    def get_all_capabilities(self):
        """
        Get all registered capabilities.

        Returns:
            dict: {capability_name: [modules]}
        """
        return {
            cap: sorted(list(modules))
            for cap, modules in self._in_memory_registry.items()
        }

    @api.model
    def get_dependency_chain(self, capability_name):
        """
        Return ordered list of modules needed for a capability.

        Args:
            capability_name (str): Target capability

        Returns:
            list: Ordered list of required modules
        """
        try:
            capabilities_needed = self._get_capability_dependencies(capability_name)
            modules = set()

            for cap in capabilities_needed:
                modules.update(self.get_modules_for(cap))

            # Add the capability itself
            modules.update(self.get_modules_for(capability_name))

            return sorted(modules)  # Deterministic order
        except Exception as e:
            _logger.error(f"Error getting dependency chain for {capability_name}: {str(e)}")
            return []

    @api.model
    def _get_capability_dependencies(self, capability_name):
        """
        Return capabilities needed to provide this one.

        Args:
            capability_name (str): Target capability

        Returns:
            list: List of prerequisite capability names
        """
        return self._capability_dependencies.get(capability_name, [])

    @api.model
    def validate_capability(self, capability_name):
        """
        Validate that a capability and all its dependencies are available.

        Args:
            capability_name (str): Capability to validate

        Returns:
            dict: {
                'valid': bool,
                'missing': [list of missing capabilities],
                'chain': [ordered modules needed]
            }
        """
        dependencies = self._get_capability_dependencies(capability_name)
        all_deps = [capability_name] + dependencies

        missing = []
        for cap in all_deps:
            if not self.is_available(cap):
                missing.append(cap)

        return {
            'valid': len(missing) == 0,
            'missing': missing,
            'chain': self.get_dependency_chain(capability_name),
        }

    @api.model
    def get_registry_status(self):
        """
        Get complete status of the registry.

        Returns:
            dict: Complete registry information
        """
        return {
            'capabilities': self.get_all_capabilities(),
            'registry': dict(self._in_memory_registry),
            'capability_dependencies': self._capability_dependencies,
        }
